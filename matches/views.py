from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from users.permissions import ensure_can_manage_team, get_user_team

from .forms import MatchForm
from .models import Match
from stats.forms import PlayerMatchStatsFormSet
from django.conf import settings
import os
from urllib.parse import quote
from stats.models import PlayerMatchStats
from players.models import Player


@login_required
def match_add_player(request, match_id):
    match = get_object_or_404(Match.objects.select_related("team"), id=match_id)
    try:
        ensure_can_manage_team(request.user, match.team)
    except PermissionDenied:
        messages.error(request, "No tienes permisos para modificar este partido.")
        return redirect("match_detail", match_id=match.id)

    # Players from the team not already associated to this match
    existing_player_ids = PlayerMatchStats.objects.filter(match=match).values_list("player_id", flat=True)
    available_players = Player.objects.filter(team=match.team).exclude(id__in=existing_player_ids).order_by("nickname")

    if request.method == "POST":
        player_id = request.POST.get("player")
        try:
            player = available_players.get(id=player_id)
        except Player.DoesNotExist:
            messages.error(request, "Selecciona un jugador válido.")
            return redirect("match_add_player", match_id=match.id)

        # Default stats for new association
        PlayerMatchStats.objects.create(
            player=player,
            match=match,
            agent_name="",
            kills=0,
            deaths=0,
            assists=0,
            won=(match.result == Match.ResultType.WIN) if match.result != Match.ResultType.PENDING else False,
        )
        messages.success(request, f"Jugador {player.nickname} añadido al partido.")
        return redirect("match_detail", match_id=match.id)

    return render(request, "matches/match_add_player.html", {"match": match, "available_players": available_players})


@login_required
def match_list(request):
    if getattr(request.user, "role", "").lower() == "admin":
        matches = Match.objects.select_related("team", "tournament").all()
    else:
        team = get_user_team(request.user)
        matches = (
            Match.objects.select_related("team", "tournament").filter(team=team)
            if team
            else Match.objects.none()
        )
    # Annotate matches with a representative map_name and banner url (if available)
    matches_with_maps = []
    for m in matches:
        # map_name is stored on the Match model
        map_name = (m.map_name or '').strip()
        banner_url = ''
        if map_name:
            # look for a file in assets/maps matching the map_name
            candidate = f"{map_name}.png"
            assets_path = os.path.join(settings.BASE_DIR, 'assets', 'maps', candidate)
            if os.path.exists(assets_path):
                banner_url = settings.STATIC_URL.rstrip('/') + '/maps/' + quote(candidate)
        matches_with_maps.append({'match': m, 'map_name': map_name, 'banner_url': banner_url})

    return render(request, "matches/match_list.html", {"matches": matches_with_maps})


@login_required
def match_detail(request, match_id):
    match = get_object_or_404(Match.objects.select_related("team", "tournament"), id=match_id)
    try:
        ensure_can_manage_team(request.user, match.team)
    except PermissionDenied:
        messages.error(request, "No tienes permisos para ver este partido.")
        return redirect("match_list")
    # use the Match.map_name as the representative map and banner
    map_name = (match.map_name or '').strip()
    banner_url = ''
    if map_name:
        candidate = f"{map_name}.png"
        assets_path = os.path.join(settings.BASE_DIR, 'assets', 'maps', candidate)
        if os.path.exists(assets_path):
            banner_url = settings.STATIC_URL.rstrip('/') + '/maps/' + quote(candidate)

    # load per-player stats for this match to show in the match detail
    map_results = (
        PlayerMatchStats.objects.filter(match=match)
        .select_related('player')
        .order_by('-won', 'player__nickname')
    )

    return render(
        request,
        "matches/match_detail.html",
        {"match": match, "map_name": map_name, "banner_url": banner_url, "map_results": map_results},
    )


@login_required
def match_create(request):
    if request.method == "POST":
        form = MatchForm(request.POST, user=request.user)
        if form.is_valid():
            match = form.save(commit=False)
            match.created_by = request.user
            match.save()
            return redirect("match_detail", match_id=match.id)
    else:
        form = MatchForm(user=request.user)

    return render(request, "matches/match_form.html", {"form": form, "mode": "create"})


@login_required
def match_update(request, match_id):
    match = get_object_or_404(Match.objects.select_related("team"), id=match_id)
    try:
        ensure_can_manage_team(request.user, match.team)
    except PermissionDenied:
        messages.error(request, "No tienes permisos para editar este partido.")
        return redirect("match_detail", match_id=match.id)  # type: ignore

    if request.method == "POST":
        form = MatchForm(request.POST, instance=match, user=request.user)
        if form.is_valid():
            form.save()
            return redirect("match_detail", match_id=match.id)  # type: ignore
    else:
        form = MatchForm(instance=match, user=request.user)

    return render(request, "matches/match_form.html", {"form": form, "mode": "edit", "match": match})  # type: ignore


@login_required
def match_delete(request, match_id):
    match = get_object_or_404(Match.objects.select_related("team"), id=match_id)
    try:
        ensure_can_manage_team(request.user, match.team)
    except PermissionDenied:
        messages.error(request, "No tienes permisos para borrar este partido.")
        return redirect("match_detail", match_id=match.id)  # type: ignore

    if request.method == "POST":
        match.delete()
        messages.success(request, "Partido eliminado.")
        return redirect("match_list")

    return render(request, "matches/match_confirm_delete.html", {"match": match})


@login_required
def match_create_with_stats(request):
    """Vista integrada para crear un partido y sus estadísticas en una sola pantalla."""
    if request.method == "POST":
        match_form = MatchForm(request.POST, user=request.user)
        if match_form.is_valid():
            match = match_form.save(commit=False)
            match.created_by = request.user
            match.save()
            
            formset = PlayerMatchStatsFormSet(request.POST, instance=match, user=request.user)
            if formset.is_valid():
                formset.save()
                messages.success(request, "Partido y estadísticas creados correctamente.")
                return redirect("match_detail", match_id=match.id)  # type: ignore
            else:
                # Si el formset falla, mostrar errores pero mantener el match creado
                return render(request, "matches/match_create_with_stats.html", {
                    "match_form": match_form,
                    "formset": formset,
                    "match": match
                })
        else:
            formset = PlayerMatchStatsFormSet(user=request.user)
    else:
        match_form = MatchForm(user=request.user)
        formset = PlayerMatchStatsFormSet(user=request.user)

    return render(request, "matches/match_create_with_stats.html", {
        "match_form": match_form,
        "formset": formset
    })