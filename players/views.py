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

# ==============================================================================
# VISTA: LISTADO DE JUGADORES
# ==============================================================================
@login_required
def player_list(request):
    # Si el usuario es administrador global, obtiene todos los jugadores de la base de datos
    if request.user.role == "admin":
        players = Player.objects.select_related("team").all()
    # Si es Coach/Mánager, obtiene solo los jugadores que pertenecen a su equipo asignado
    else:
        team = get_user_team(request.user)
        # select_related("team") hace un JOIN en SQL para traer los datos del equipo en una sola consulta
        players = Player.objects.select_related("team").filter(team=team) if team else Player.objects.none()
    
    return render(request, "players/player_list.html", {"players": players})


# ==============================================================================
# VISTA: DETALLE DEL JUGADOR (Perfil de Rendimiento)
# ==============================================================================
@login_required
def player_detail(request, player_id):
    # Obtiene el jugador por su ID o lanza un error 404 si no existe
    player = get_object_or_404(Player.objects.select_related("team"), id=player_id)
    
    # SEGURIDAD: Comprueba si el usuario logueado tiene permiso para gestionar el equipo de este jugador
    ensure_can_manage_team(request.user, player.team)
    
    # Obtiene la relación inversa de estadísticas mapeadas a este jugador
    player_stats = cast(Any, player).stats
    
    # Obtiene los últimos 5 mapas/partidos jugados con resultado definitivo (excluye pendientes)
    recent_stats = (
        player_stats.select_related("match", "match__team")
        .filter(match__result__in=[Match.ResultType.WIN, Match.ResultType.LOSS])
        .order_by("-match__date")[:5] # Ordena de más reciente a más antiguo y limita a 5
    )
    
    return render(request, "players/player_detail.html", {"player": player, "recent_stats": recent_stats})


# ==============================================================================
# VISTA: CREAR JUGADOR (Fichajes)
# ==============================================================================
@login_required
def player_create(request):
    # Captura variables opcionales de la URL para mejorar la UX (ej: ?team=2&next=/teams/detail/2)
    team_prefill_id = request.GET.get("team") # ID del equipo para preseleccionar en el desplegable
    return_to = request.GET.get("next")       # URL a la que redirigir tras guardar con éxito

    if request.method == "POST":
        # Pasa el usuario actual al formulario para que aplique sus filtros de seguridad internos
        form = PlayerForm(request.POST, user=request.user) # type: ignore
        if form.is_valid():
            # Crea el objeto Jugador en memoria sin guardarlo en la base de datos todavía
            player = form.save(commit=False)

            # SEGURIDAD BACKEND: Doble verificación. Asegura que el usuario puede meter datos en ese equipo.
            ensure_can_manage_team(request.user, player.team)
            player.save() # Guarda el registro definitivo en la base de datos
            
            # Control de redirecciones dinámicas según los parámetros del sistema
            if request.POST.get("next"):
                return redirect(request.POST.get("next"))
            if return_to:
                return redirect(return_to)
            return redirect("player_detail", player_id=player.id)
    else:
        # Petición GET: Inicializa el formulario de creación vacío
        form = PlayerForm(user=request.user) # type: ignore

        # LÓGICA DE PRE-RELLENADO (Si venimos, por ejemplo, desde la vista del detalle de un equipo)
        if team_prefill_id:
            try:
                team_obj = Team.objects.get(id=team_prefill_id)
                try:
                    # Comprueba que el usuario tiene derecho a añadir gente a ese equipo pre-rellenado
                    ensure_can_manage_team(request.user, team_obj)
                except PermissionDenied:
                    # Si intenta hacer trampas cambiando el ID de la URL por un equipo rival, se ignora el pre-rellenado
                    team_obj = None
                
                if team_obj:
                    # Modifica el formulario sobre la marcha: bloquea el desplegable a ese único equipo y lo preselecciona
                    form.fields["team"].queryset = form.fields["team"].queryset.filter(id=team_obj.id) # type: ignore
                    form.initial["team"] = team_obj
            except Team.DoesNotExist:
                pass # Si el equipo metido por la URL no existe, no hace nada y continúa de forma segura

        # SEGURIDAD EXTRA: Si no es administrador, limita el desplegable de equipos única y exclusivamente al suyo
        if request.user.role != "admin":
            team = get_user_team(request.user)
            if team:
                form.fields["team"].queryset = form.fields["team"].queryset.filter(id=team.id) # type: ignore
            else:
                form.fields["team"].queryset = form.fields["team"].queryset.none() # type: ignore

    return render(request, "players/player_form.html", {"form": form, "mode": "create", "next": return_to})


# ==============================================================================
# VISTA: MODIFICAR JUGADOR (Editar perfil)
# ==============================================================================
@login_required
def player_update(request, player_id):
    # Busca el jugador a modificar
    player = get_object_or_404(Player.objects.select_related("team"), id=player_id)
    # SEGURIDAD: Comprueba que el usuario puede editar datos en el equipo actual de ese jugador
    ensure_can_manage_team(request.user, player.team)

    if request.method == "POST":
        # Pasa los datos nuevos adjuntando la instancia del jugador original
        form = PlayerForm(request.POST, instance=player, user=request.user) # type: ignore
        if form.is_valid():
            updated = form.save(commit=False)
            # SEGURIDAD: Comprueba que el usuario tenga permisos sobre el equipo NUEVO (por si se edita el club)
            ensure_can_manage_team(request.user, updated.team)
            updated.save()
            return redirect("player_detail", player_id=player.id) # type: ignore
    else:
        # Petición GET: Carga el formulario relleno con los datos actuales del jugador
        form = PlayerForm(instance=player, user=request.user) # type: ignore
        # Si no es admin, blinda el desplegable para que no pueda transferirse el jugador a un club ajeno
        if request.user.role != "admin":
            team = get_user_team(request.user)
            if team:
                form.fields["team"].queryset = form.fields["team"].queryset.filter(id=team.id) # type: ignore
            else:
                form.fields["team"].queryset = form.fields["team"].queryset.none() # type: ignore

    return render(request, "players/player_form.html", {"form": form, "player": player, "mode": "edit"})


# ==============================================================================
# VISTA: ELIMINAR JUGADOR (Baja del sistema)
# ==============================================================================
@login_required
def player_delete(request, player_id):
    # Busca al jugador
    player = get_object_or_404(Player.objects.select_related("team"), id=player_id)
    # SEGURIDAD: Control de acceso para el borrado
    try:
        ensure_can_manage_team(request.user, player.team)
    except PermissionDenied:
        messages.error(request, "No tienes permisos para eliminar este jugador.")
        return redirect("player_list")

    if request.method == "POST":
        player.delete() # Borra el registro de la base de datos de forma definitiva
        return redirect("player_list")

    return render(request, "players/player_confirm_delete.html", {"player": player})