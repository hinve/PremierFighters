from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from typing import Any, cast

from django.core.exceptions import PermissionDenied
from django.contrib import messages
from matches.models import Match
from teams.models import Team
from users.permissions import ensure_can_manage_team, get_user_team

from .forms import PlayerForm
from .models import Player


@login_required
def player_list(request):
    if request.user.role == "admin":
        players = Player.objects.select_related("team").all()
    else:
        team = get_user_team(request.user)
        players = Player.objects.select_related("team").filter(team=team) if team else Player.objects.none()
    return render(request, "players/player_list.html", {"players": players})


@login_required
def player_detail(request, player_id):
    player = get_object_or_404(Player.objects.select_related("team"), id=player_id)
    ensure_can_manage_team(request.user, player.team)
    player_stats = cast(Any, player).stats
    recent_stats = (
        player_stats.select_related("match", "match__team")
        .filter(match__result__in=[Match.ResultType.WIN, Match.ResultType.LOSS])
        .order_by("-match__date")[:5]
    )
    return render(request, "players/player_detail.html", {"player": player, "recent_stats": recent_stats})


@login_required
def player_create(request):
    # Allow prefilling team via GET parameter and return via `next`
    team_prefill_id = request.GET.get("team")
    return_to = request.GET.get("next")

    if request.method == "POST":
        form = PlayerForm(request.POST, user=request.user) # type: ignore
        if form.is_valid():
            player = form.save(commit=False)

            # Validación de permisos por equipo antes de guardar
            ensure_can_manage_team(request.user, player.team)
            player.save()
            if request.POST.get("next"):
                return redirect(request.POST.get("next"))
            if return_to:
                return redirect(return_to)
            return redirect("player_detail", player_id=player.id)
    else:
        form = PlayerForm(user=request.user) # type: ignore

        # If team prefilling is requested, limit selectable teams and set initial
        if team_prefill_id:
            try:
                team_obj = Team.objects.get(id=team_prefill_id)
                # Ensure user can manage this team before preselecting
                try:
                    ensure_can_manage_team(request.user, team_obj)
                except PermissionDenied:
                    # If user cannot manage the team, ignore prefill
                    team_obj = None
                if team_obj:
                    form.fields["team"].queryset = form.fields["team"].queryset.filter(id=team_obj.id) # type: ignore
                    form.initial["team"] = team_obj
            except Team.DoesNotExist:
                pass

        # Si no es admin, limitar equipos seleccionables al suyo
        if request.user.role != "admin":
            team = get_user_team(request.user)
            if team:
                form.fields["team"].queryset = form.fields["team"].queryset.filter(id=team.id) # type: ignore
            else:
                form.fields["team"].queryset = form.fields["team"].queryset.none() # type: ignore

    return render(request, "players/player_form.html", {"form": form, "mode": "create", "next": return_to})


@login_required
def player_update(request, player_id):
    player = get_object_or_404(Player.objects.select_related("team"), id=player_id)
    ensure_can_manage_team(request.user, player.team)

    if request.method == "POST":
        form = PlayerForm(request.POST, instance=player, user=request.user) # type: ignore
        if form.is_valid():
            updated = form.save(commit=False)
            ensure_can_manage_team(request.user, updated.team)
            updated.save()
            return redirect("player_detail", player_id=player.id) # type: ignore
    else:
        form = PlayerForm(instance=player, user=request.user) # type: ignore
        if request.user.role != "admin":
            team = get_user_team(request.user)
            if team:
                form.fields["team"].queryset = form.fields["team"].queryset.filter(id=team.id) # type: ignore
            else:
                form.fields["team"].queryset = form.fields["team"].queryset.none() # type: ignore

    return render(request, "players/player_form.html", {"form": form, "player": player, "mode": "edit"})


@login_required
def player_delete(request, player_id):
    player = get_object_or_404(Player.objects.select_related("team"), id=player_id)
    try:
        ensure_can_manage_team(request.user, player.team)
    except PermissionDenied:
        messages.error(request, "No tienes permisos para ...")
        return redirect("player_list")

    if request.method == "POST":
        player.delete()
        return redirect("player_list")

    return render(request, "players/player_confirm_delete.html", {"player": player})