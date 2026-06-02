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

# ==============================================================================
# FUNCIONES AUXILIARES / MÉTODOS PRIVADOS (Encapsulación de lógica de filtrado)
# ==============================================================================

def _get_accessible_matches(user):
    """Retorna los partidos que el usuario tiene derecho a ver según su rol."""
    if getattr(user, "role", "").lower() == "admin":
        return Match.objects.select_related("team", "tournament").all().order_by("-date")

    team = get_user_team(user)
    if team:
        return Match.objects.select_related("team", "tournament").filter(team=team).order_by("-date")
    return Match.objects.none()


def _get_match_for_user(user, match_id):
    """Busca un partido específico asegurando que pertenezca al set accesible del usuario."""
    accessible_matches = _get_accessible_matches(user)
    return accessible_matches.filter(id=match_id).first()


# ==============================================================================
# VISTA: LISTADO GLOBAL DE ESTADÍSTICAS
# ==============================================================================
@login_required
def mapresult_list(request):
    # Seguridad y optimización: Los admins ven todo, los coaches ven solo su club. Usa select_related para evitar N+1
    if getattr(request.user, "role", "").lower() == "admin":
        stats = PlayerMatchStats.objects.select_related("player", "match", "match__team").all()
    else:
        team = get_user_team(request.user)
        stats = (
            PlayerMatchStats.objects.select_related("player", "match", "match__team").filter(match__team=team)
            if team else PlayerMatchStats.objects.none()
        )

    return render(request, "stats/mapresult_list.html", {"stats": stats})


# ==============================================================================
# VISTA: DETALLE DE UNA ESTADÍSTICA INDIVIDUAL
# ==============================================================================
@login_required
def mapresult_detail(request, stat_id):
    stat = get_object_or_404(PlayerMatchStats.objects.select_related("player", "match", "match__team"), id=stat_id)
    try:
        ensure_can_manage_team(request.user, stat.match.team)
    except PermissionDenied:
        messages.error(request, "No tienes permisos para ver este resultado de mapa.")
        return redirect("match_list")

    return render(request, "stats/mapresult_detail.html", {"stat": stat})


# ==============================================================================
# VISTA COMPLEJA: CREACIÓN/EDICIÓN SIMULTÁNEA POR LOTES (Alineación Completa)
# ==============================================================================
@login_required
def mapresult_create(request):
    # 1. Determina el partido seleccionado (ya sea por envío del formulario POST o por parámetro GET de la URL)
    selected_match_id = request.POST.get("match_id") if request.method == "POST" else request.GET.get("match")
    selected_match = _get_match_for_user(request.user, selected_match_id) if selected_match_id else None
    selected_map_name = None

    # 2. Inicializa el formulario de selección de partido aplicando los bloqueos de seguridad por usuario
    if request.method == "POST":
        selection_form = MatchSelectionForm({"match": selected_match_id}, user=request.user)
    else:
        selection_form = MatchSelectionForm(request.GET, user=request.user)
    
    if selected_match:
        selection_form.initial = {"match": selected_match}
    
    # Inicializa el formulario global del estado del mapa (Victoria/Derrota)
    batch_form = MapResultBatchForm(request.POST if request.method == "POST" else None)
    player_forms = []
    
    # 3. Recupera estadísticas preexistentes de este partido para permitir la reedición en bloque
    existing_stats = list(
        PlayerMatchStats.objects.select_related("player", "match", "match__team").filter(match=selected_match).order_by("-id")
    ) if selected_match else []

    # Obtiene la lista de jugadores que pertenecen al equipo del partido actual
    players = list(cast(Any, selected_match.team).players.select_related("team").order_by("nickname")) if selected_match else []
    # Mapea las estadísticas existentes en un diccionario {player_id: objeto_stat} para buscarlas a velocidad O(1)
    existing_stats_for_map = {cast(Any, stat.player).id: stat for stat in existing_stats}

    # Si es una carga inicial (GET) y el partido ya tiene un resultado general, lo preselecciona en el botón de radio
    if request.method != "POST" and selected_match:
        batch_form = MapResultBatchForm(
            initial={
                "won": "true" if selected_match.result == Match.ResultType.WIN else "false" if selected_match.result == Match.ResultType.LOSS else "true",
            }
        )

    # 4. CONSTRUCCIÓN DE LA REJILLA DINÁMICA (Genera una fila por cada jugador del equipo)
    if selected_match:
        for player in players:
            prefix = f"player-{player.id}"  # El prefijo evita colisiones de nombres de campos en el HTML request.POST
            initial = {}
            existing_stat = existing_stats_for_map.get(player.id)
            
            # Si el jugador ya tenía datos guardados en este partido, los precarga en su fila correspondiente
            if existing_stat:
                initial = {
                    "agent_name": existing_stat.agent_name,
                    "kills": existing_stat.kills,
                    "deaths": existing_stat.deaths,
                    "assists": existing_stat.assists,
                }
            
            # Enlaza los datos del POST o del GET usando el prefijo identificador único del jugador
            if request.method == "POST":
                form = MapResultPlayerRowForm(request.POST, prefix=prefix)
            else:
                form = MapResultPlayerRowForm(prefix=prefix, initial=initial)
            
            player_forms.append({"player": player, "form": form})

    # 5. PROCESAMIENTO Y GUARDADO DE DATOS (Petición POST)
    if request.method == "POST" and selected_match:
        if not selection_form.is_valid():
            messages.error(request, "Selecciona un partido válido.")
        
        if batch_form.is_valid():
            total_form_errors = 0

            # Valida una por una todas las filas de los jugadores en la rejilla
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

            # 6. PERSISTENCIA ATÓMICA SI TODO ES VÁLIDO
            if total_form_errors == 0:
                won_value = batch_form.cleaned_data["won"] == "true"
                
                # Seguridad estricta: Verifica que el usuario tiene control sobre el club antes de escribir en BD
                try:
                    ensure_can_manage_team(request.user, selected_match.team)
                except PermissionDenied:
                    messages.error(request, "No tienes permisos para crear estadísticas en este equipo.")
                    return redirect("match_detail", match_id=selected_match.pk)

                # Ejecuta la inserción o actualización masiva en la base de datos
                for row in player_forms:
                    player = row["player"]
                    form = row["form"]
                    cleaned = form.cleaned_data
                    
                    # update_or_create evita duplicados: si la fila existe la actualiza, si no, la inserta.
                    PlayerMatchStats.objects.update_or_create(
                        player=player,
                        match=selected_match,
                        defaults={
                            "agent_name": cleaned["agent_name"],
                            "kills": cleaned["kills"],
                            "deaths": cleaned["deaths"],
                            "assists": cleaned["assists"],
                            "won": won_value,  # El estado de victoria se hereda de la configuración de lote
                        },
                    )

                messages.success(request, "Resultados de mapa guardados correctamente.")
                return redirect("match_detail", match_id=selected_match.pk)

        # Alerta de lógica de negocio: Si el partido está pendiente, advierte que los cálculos K/D quedarán en pausa
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


# ==============================================================================
# VISTAS CRUD ESTÁNDAR: ACTUALIZAR Y ELIMINAR REGISTROS INDIVIDUALES
# ==============================================================================
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
            # REGLA DE NEGOCIO INTERNA: Evita corrupciones (ej: meter estadísticas de un jugador de KOI en un partido de KPI)
            if updated.player.team_id != updated.match.team_id:
                form.add_error(None, "El jugador y el partido deben pertenecer al mismo equipo.")
            else:
                updated.save()
                return redirect("match_detail", match_id=stat.match.id)  # type: ignore
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
        return redirect("match_detail", match_id=stat.match.id)  # type: ignore

    return render(request, "stats/mapresult_confirm_delete.html", {"stat": stat})