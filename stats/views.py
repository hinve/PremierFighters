from typing import Any, cast

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from urllib.parse import urlencode

from matches.models import Match
from users.permissions import ensure_can_manage_team, get_user_team

from .forms import MapResultBatchForm, MapResultPlayerRowForm, MatchSelectionForm, PlayerMatchStatsForm
from .models import PlayerMatchStats


def _get_accessible_matches(user):
    if getattr(user, "role", "").lower() == "admin":
        return Match.objects.select_related("team", "tournament").all().order_by("-date")

    team = get_user_team(user)
    if team:
        return Match.objects.select_related("team", "tournament").filter(team=team).order_by("-date")
    return Match.objects.none()


def _get_match_for_user(user, match_id):
    accessible_matches = _get_accessible_matches(user)
    return accessible_matches.filter(id=match_id).first()


@login_required
def mapresult_list(request):
    if getattr(request.user, "role", "").lower() == "admin":
        stats = PlayerMatchStats.objects.select_related("player", "match", "match__team").all()
    else:
        team = get_user_team(request.user)
        stats = (
            PlayerMatchStats.objects.select_related("player", "match", "match__team").filter(match__team=team)
            if team
            else PlayerMatchStats.objects.none()
        )

    return render(request, "stats/mapresult_list.html", {"stats": stats})


@login_required
def mapresult_detail(request, stat_id):
    stat = get_object_or_404(PlayerMatchStats.objects.select_related("player", "match", "match__team"), id=stat_id)
    try:
        ensure_can_manage_team(request.user, stat.match.team)
    except PermissionDenied:
        messages.error(request, "No tienes permisos para ver este resultado de mapa.")
        return redirect("match_list")

    return render(request, "stats/mapresult_detail.html", {"stat": stat})


@login_required
def mapresult_create(request):
    selected_match_id = request.POST.get("match_id") if request.method == "POST" else request.GET.get("match")
    selected_match = _get_match_for_user(request.user, selected_match_id) if selected_match_id else None
    # map_name is stored on the Match model; do not take it from the request
    selected_map_name = None

    # Bind the selection form from GET normally, but when POSTing use the posted match_id
    if request.method == "POST":
        selection_form = MatchSelectionForm({"match": selected_match_id}, user=request.user)
    else:
        selection_form = MatchSelectionForm(request.GET, user=request.user)
    if selected_match:
        selection_form.initial = {"match": selected_match}
    batch_form = MapResultBatchForm(request.POST if request.method == "POST" else None)
    player_forms = []
    existing_stats = list(
        PlayerMatchStats.objects.select_related("player", "match", "match__team").filter(match=selected_match).order_by("-id")
    ) if selected_match else []
    # No per-map names in PlayerMatchStats anymore; we rely on selected_match.map_name

    players = list(cast(Any, selected_match.team).players.select_related("team").order_by("nickname")) if selected_match else []
    existing_stats_for_map = {cast(Any, stat.player).id: stat for stat in existing_stats}

    if request.method != "POST" and selected_match:
        batch_form = MapResultBatchForm(
            initial={
                "won": "true" if selected_match.result == Match.ResultType.WIN else "false" if selected_match.result == Match.ResultType.LOSS else "true",
            }
        )

    if selected_match:
        for player in players:
            prefix = f"player-{player.id}"
            initial = {}
            existing_stat = existing_stats_for_map.get(player.id)
            if existing_stat:
                initial = {
                    "agent_name": existing_stat.agent_name,
                    "kills": existing_stat.kills,
                    "deaths": existing_stat.deaths,
                    "assists": existing_stat.assists,
                }
            if request.method == "POST":
                form = MapResultPlayerRowForm(request.POST, prefix=prefix)
            else:
                form = MapResultPlayerRowForm(prefix=prefix, initial=initial)
            player_forms.append({"player": player, "form": form})

    if request.method == "POST" and selected_match:
        if not selection_form.is_valid():
            messages.error(request, "Selecciona un partido válido.")
        if batch_form.is_valid():
            total_form_errors = 0

            for row in player_forms:
                player = row["player"]
                form = row["form"]
                existing_stat = PlayerMatchStats.objects.filter(
                    player=player,
                    match=selected_match,
                ).first()
                if existing_stat and request.method == "GET":
                    form = MapResultPlayerRowForm(prefix=f"player-{player.id}", initial={
                        "agent_name": existing_stat.agent_name,
                        "kills": existing_stat.kills,
                        "deaths": existing_stat.deaths,
                        "assists": existing_stat.assists,
                    })

                if not form.is_valid():
                    total_form_errors += 1

            if total_form_errors == 0:
                won_value = batch_form.cleaned_data["won"] == "true"
                try:
                    ensure_can_manage_team(request.user, selected_match.team)
                except PermissionDenied:
                    messages.error(request, "No tienes permisos para crear estadísticas en este equipo.")
                    return redirect("match_detail", match_id=selected_match.pk)

                for row in player_forms:
                    player = row["player"]
                    form = row["form"]
                    cleaned = form.cleaned_data
                    PlayerMatchStats.objects.update_or_create(
                        player=player,
                        match=selected_match,
                        defaults={
                            "agent_name": cleaned["agent_name"],
                            "kills": cleaned["kills"],
                            "deaths": cleaned["deaths"],
                            "assists": cleaned["assists"],
                            "won": won_value,
                        },
                    )

                messages.success(request, "Resultados de mapa guardados correctamente.")
                return redirect("match_detail", match_id=selected_match.pk)

        if selected_match.result == Match.ResultType.PENDING:
            messages.warning(request, "Este partido todavía está pendiente. El resultado del mapa se puede guardar, pero no contará en los cálculos hasta que el partido esté decidido.")

    return render(
        request,
        "stats/mapresult_form.html",
        {
            "selection_form": selection_form,
            "batch_form": batch_form,
            "player_forms": player_forms,
            "selected_match": selected_match,
            "mode": "create",
        },
    )


@login_required
def mapresult_update(request, stat_id):
    stat = get_object_or_404(PlayerMatchStats.objects.select_related("player", "match", "match__team"), id=stat_id)
    try:
        ensure_can_manage_team(request.user, stat.match.team)
    except PermissionDenied:
        messages.error(request, "No tienes permisos para editar este resultado de mapa.")
        return redirect("match_list")

    if request.method == "POST":
        form = PlayerMatchStatsForm(request.POST, instance=stat, user=request.user)
        if form.is_valid():
            updated = form.save(commit=False)
            if updated.player.team_id != updated.match.team_id:
                form.add_error(None, "El jugador y el partido deben pertenecer al mismo equipo.")
            else:
                updated.save()
                return redirect("match_detail", match_id=stat.match.id) # type: ignore
    else:
        form = PlayerMatchStatsForm(instance=stat, user=request.user)

    return render(request, "stats/mapresult_form.html", {"form": form, "stat": stat, "mode": "edit"})


@login_required
def mapresult_delete(request, stat_id):
    stat = get_object_or_404(PlayerMatchStats.objects.select_related("player", "match", "match__team"), id=stat_id)
    try:
        ensure_can_manage_team(request.user, stat.match.team)
    except PermissionDenied:
        messages.error(request, "No tienes permisos para borrar este resultado de mapa.")
        return redirect("match_list")

    if request.method == "POST":
        stat.delete()
        messages.success(request, "Resultado de mapa eliminado.")
        return redirect("match_detail", match_id=stat.match.id) # type: ignore

    return render(request, "stats/mapresult_confirm_delete.html", {"stat": stat})