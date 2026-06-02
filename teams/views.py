from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from matches.models import Match
from users.permissions import ensure_can_manage_team, get_user_team

from .forms import TeamForm
from .models import Team

# ==============================================================================
# VISTA: LISTADO DE EQUIPOS
# ==============================================================================
@login_required
def team_list(request):
    # Si el usuario es administrador global, puede ver todos los equipos registrados
    if request.user.role == "admin":
        teams = Team.objects.all()
    # Si es Coach/Mánager, el sistema lo aísla para que solo vea su propio equipo
    else:
        team = get_user_team(request.user)
        # Si el usuario tiene un equipo asignado lo filtra, de lo contrario devuelve un set vacío
        teams = Team.objects.filter(id=team.id) if team else Team.objects.none()
    
    return render(request, "teams/team_list.html", {"teams": teams})


# ==============================================================================
# VISTA: DETALLE DEL EQUIPO (Organigrama y Perfil del Club)
# ==============================================================================
@login_required
def team_detail(request, team_id):
    # Recupera el club por su ID o lanza un error 404 si no existe
    team = get_object_or_404(Team, id=team_id)
    # Mantiene la regla de acceso libre para visualización interna del club
    return render(request, "teams/team_detail.html", {"team": team})


# ==============================================================================
# VISTA: CREAR EQUIPO (Inscripción de Clubes)
# ==============================================================================
@login_required
def team_create(request):
    # CONTROL DE SEGURIDAD EXTRALIMITADA: Si no es admin, evitamos que cree múltiples clubes
    if request.user.role != "admin":
        my_team = get_user_team(request.user)
        # Si este Coach o Mánager ya tiene una organización asignada, lo redirigimos a ella directamente
        if my_team:
            return redirect("team_detail", team_id=my_team.id)

    if request.method == "POST":
        form = TeamForm(request.POST)
        if form.is_valid():
            # Guarda los datos iniciales del club en la base de datos
            team = form.save()

            # LÓGICA DE AUTOASIGNACIÓN: Si el creador no es admin, se autoasigna como staff del club recién creado
            if request.user.role == "coach" and not team.coach:
                team.coach = request.user
                team.save()
            elif request.user.role == "manager" and not team.manager:
                team.manager = request.user
                team.save()

            return redirect("team_detail", team_id=team.id)
    else:
        # Petición GET: Inicializa el formulario de creación vacío
        form = TeamForm()

    return render(request, "teams/team_form.html", {"form": form, "mode": "create"})


# ==============================================================================
# VISTA: MODIFICAR EQUIPO (Editar Datos de Franquicia)
# ==============================================================================
@login_required
def team_update(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    # SEGURIDAD BACKEND: Comprueba de forma estricta si el usuario logueado puede gestionar este club específico
    try:
        ensure_can_manage_team(request.user, team)
    except PermissionDenied:
        messages.error(request, "No tienes permisos para editar este equipo.")
        return redirect("team_detail", team_id=team.id)  # type: ignore

    if request.method == "POST":
        # Pasa los datos del POST junto a la instancia actual para actualizar la fila exacta
        form = TeamForm(request.POST, instance=team)
        if form.is_valid():
            form.save()
            return redirect("team_detail", team_id=team.pk)
    else:
        # Petición GET: Precarga los datos del equipo en los campos de edición
        form = TeamForm(instance=team)

    return render(request, "teams/team_form.html", {"form": form, "team": team, "mode": "edit"})


# ==============================================================================
# VISTA: ELIMINAR EQUIPO (Disolución del Club)
# ==============================================================================
@login_required
def team_delete(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    # SEGURIDAD BACKEND: Evita que terceros eliminen clubes ajenos
    try:
        ensure_can_manage_team(request.user, team)
    except PermissionDenied:
        messages.error(request, "No tienes permisos para eliminar este equipo.")
        return redirect("team_detail", team_id=team.id)  # type: ignore

    if request.method == "POST":
        team.delete()  # Borra el registro de la BD (disparará el borrado en cascada de sus jugadores)
        return redirect("team_list")

    return render(request, "teams/team_confirm_delete.html", {"team": team})


# ==============================================================================
# VISTA DE ANALÍTICA AVANZADA: ESTADÍSTICAS ESTRATÉGICAS DEL CLUB
# ==============================================================================
@login_required
def team_stats(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    # SEGURIDAD BACKEND: Los datos de rendimiento estratégico están capados al staff del equipo
    try:
        ensure_can_manage_team(request.user, team)
    except PermissionDenied:
        messages.error(request, "No tienes permisos para ver las estadísticas de este equipo.")
        return redirect("team_list")

    # OPTIMIZACIÓN SQL: prefetch_related evita el problema de consultas masivas N+1 al traer todas las filas de stats de golpe
    players = team.players.prefetch_related("stats").all()  # type: ignore

    player_rows = []
    # Bucle de procesamiento algorítmico en memoria
    for player in players:
        # Obtiene el listado de registros estadísticos en encuentros resueltos (Win/Loss)
        stats = list(player.stats.filter(match__result__in=[Match.ResultType.WIN, Match.ResultType.LOSS]))
        
        # Diccionario contador de frecuencia para calcular la moda estadística de agentes usados
        agent_stats = {}
        for stat in stats:
            if stat.agent_name:
                # Suma un caso al agente correspondiente
                agent_stats[stat.agent_name] = agent_stats.get(stat.agent_name, 0) + 1

        # CÁLCULO DE LA MODA: Extrae la clave con el valor de repeticiones más alto del diccionario
        favorite_agent = max(agent_stats.items(), key=lambda item: item[1])[0] if agent_stats else "-"
        
        # Empaqueta los datos procesados del jugador en una estructura limpia para la plantilla HTML
        player_rows.append(
            {
                "player": player,
                "favorite_agent": favorite_agent,
            }
        )
    
    return render(request, "teams/team_stats.html", {"team": team, "players": player_rows})