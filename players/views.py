from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

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
    return render(request, "players/player_detail.html", {"player": player})


@login_required
def player_create(request):
    if request.method == "POST":
        form = PlayerForm(request.POST)
        if form.is_valid():
            player = form.save(commit=False)

            # Validación de permisos por equipo antes de guardar
            ensure_can_manage_team(request.user, player.team)
            player.save()
            return redirect("player_detail", player_id=player.id)
    else:
        form = PlayerForm()

        # Si no es admin, limitar equipos seleccionables al suyo
        if request.user.role != "admin":
            team = get_user_team(request.user)
            if team:
                form.fields["team"].queryset = form.fields["team"].queryset.filter(id=team.id) # type: ignore
            else:
                form.fields["team"].queryset = form.fields["team"].queryset.none() # type: ignore

    return render(request, "players/player_form.html", {"form": form, "mode": "create"})


@login_required
def player_update(request, player_id):
    player = get_object_or_404(Player.objects.select_related("team"), id=player_id)
    ensure_can_manage_team(request.user, player.team)

    if request.method == "POST":
        form = PlayerForm(request.POST, instance=player)
        if form.is_valid():
            updated = form.save(commit=False)
            ensure_can_manage_team(request.user, updated.team)
            updated.save()
            return redirect("player_detail", player_id=player.id) # type: ignore
    else:
        form = PlayerForm(instance=player)
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
    ensure_can_manage_team(request.user, player.team)

    if request.method == "POST":
        player.delete()
        return redirect("player_list")

    return render(request, "players/player_confirm_delete.html", {"player": player})