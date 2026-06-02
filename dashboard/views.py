from datetime import timedelta
from typing import Any, cast

# Mensajes flash de Django para alertas en la interfaz (ej: advertencias o éxitos)
from django.contrib import messages
# Decorador para obligar a que el usuario esté logueado antes de ver la vista
from django.contrib.auth.decorators import login_required
# Funciones de agregación del ORM de Django para contar, renombrar, filtrar y sumar en la base de datos
from django.db.models import Count, F, Q, Sum
# Función para renderizar plantillas HTML mezcladas con diccionarios de datos (contexto)
from django.shortcuts import render
# Herramienta para gestionar zonas horarias de forma correcta y segura en Django
from django.utils import timezone

# Importación de tus modelos personalizados de las distintas Apps del proyecto
from matches.models import Match
from stats.models import PlayerMatchStats
from teams.models import Team
from users.permissions import get_user_team

def _get_accessible_teams(user):
    """
    Función auxiliar (privada) para filtrar qué equipos puede ver el usuario logueado.
    Garantiza el control de acceso y seguridad del sistema.
    """
    # Si el rol del usuario es "admin", tiene acceso total y puede ver todos los equipos ordenados por nombre
    if getattr(user, "role", "").lower() == "admin":
        return Team.objects.all().order_by("name")

    # Si no es admin, obtiene el equipo asignado específicamente a ese usuario (Coach o Manager)
    team = get_user_team(user)
    if team:
        # Retorna únicamente el equipo al que pertenece el usuario
        return Team.objects.filter(id=team.id)
    
    # Si el usuario no tiene equipo asignado ni es admin, retorna un QuerySet vacío
    return Team.objects.none()

@login_required  # Si el usuario no ha iniciado sesión, Django lo redirige automáticamente al login
def home(request):
    """
    Vista principal del Dashboard. Procesa y agrupa toda la analítica de Valorant 
    (partidas, mapas, agentes y rendimiento de jugadores) para mandarla al HTML.
    """
    # 1. OBTENCIÓN Y FILTRADO DE PARÁMETROS DE LA URL (Manejo del Estado)
    teams = _get_accessible_teams(request.user)  # Equipos que este usuario tiene permiso de ver
    selected_team = None
    # Captura el ID del equipo desde los parámetros GET de la URL (soporta ?team_id= o ?team=)
    selected_team_id = request.GET.get("team_id") or request.GET.get("team")
    # Captura el mapa seleccionado en los filtros (ej: ?selected_map=Ascent)
    selected_map = request.GET.get("selected_map") or ""

    # Determina qué equipo se va a pintar en el Dashboard
    if selected_team_id:
        # Si viene un ID en la URL, busca ese equipo dentro de los permitidos para el usuario
        selected_team = teams.filter(id=selected_team_id).first()
        if not selected_team:
            messages.warning(request, "Selecciona un equipo válido para ver sus reportes.")
    elif teams.count() == 1:
        # Si el usuario solo tiene acceso a un equipo (caso típico de un Coach), lo selecciona por defecto
        selected_team = teams.first()

    # 2. INICIALIZACIÓN DEL CONTEXTO BASE (Valores por defecto para evitar errores en el HTML)
    context = {
        "teams": teams,
        "selected_team": selected_team,
        "selected_team_id": getattr(selected_team, "id", None),
        "selected_map": selected_map,
        "team_summary": None,
        "recent_scrims": [],
        "pending_matches": [],
        "calendar_days": [],
        "player_rows": [],
        "map_rows": [],
        "evolution_rows": [],
        # Simulación/Estructura temporal para una futura integración con la API oficial de Riot Games
        "riot_placeholder": {
            "status": "Pendiente",
            "features": [
                "Perfil de Riot ID / Summoner",
                "Ranked queue y tier actual",
                "Historial de partidas ranked",
                "Pool de campeones y rendimiento",
            ],
        },
    }

    # Si no hay ningún equipo seleccionado, renderiza la página limpia (solo con el selector de equipos)
    if not selected_team:
        return render(request, "dashboard/home.html", context)

    # Forzado de tipado dinámico para evitar advertencias del linter de código
    team = cast(Any, selected_team)
    
    # Definición de estados finales de un partido (Ganado o Perdido). Excluye los pendientes.
    decided_results = [Match.ResultType.WIN, Match.ResultType.LOSS]

    # Gestión de fechas actuales del sistema
    now = timezone.now()
    today = timezone.localdate()

    # 3. ANALÍTICA GENERAL DE PARTIDOS DEL EQUIPO
    # Filtra los partidos que ya se han jugado y tienen un resultado definitivo
    decided_matches = team.matches.filter(result__in=decided_results)
    total_matches = decided_matches.count()
    # Cuenta cuántos partidos terminaron en victoria
    wins = decided_matches.filter(result=Match.ResultType.WIN).count()
    losses = total_matches - wins  # El resto son derrotas
    decided_count = decided_matches.count()
    # Cuenta las scrims (partidas de entrenamiento) jugadas
    scrims_count = decided_matches.filter(match_type=Match.MatchType.SCRIM).count()
    
    # Obtiene las últimas 5 scrims jugadas optimizando la consulta con select_related para traer la info del torneo
    scrim_matches = (
        decided_matches.filter(match_type=Match.MatchType.SCRIM)
        .select_related("tournament")
        .order_by("-date")[:5]
    )
    # Obtiene los próximos 5 partidos agendados (pendientes) ordenados de más cercano a más lejano
    pending_matches = team.matches.filter(result=Match.ResultType.PENDING).select_related("tournament").order_by("date")[:5]

    # 4. GENERACIÓN DEL CALENDARIO SEMANAL (Próximos 7 días)
    calendar_start = today
    calendar_end = today + timedelta(days=6)
    # Trae los partidos programados en ese rango de 7 días
    calendar_matches = team.matches.filter(date__date__range=(calendar_start, calendar_end)).order_by("date")
    
    # Crea un diccionario donde las llaves son los próximos 7 días con listas vacías como valores por defecto
    calendar_map = {calendar_start + timedelta(days=offset): [] for offset in range(7)}
    # Clasifica cada partido en su día correspondiente del calendario
    for match in calendar_matches:
        match_day = timezone.localdate(match.date)
        if match_day in calendar_map:
            calendar_map[match_day].append(match)

    # Estructura el calendario en una lista de diccionarios para que el HTML lo pueda iterar y pintar fácilmente
    calendar_days = []
    for offset in range(7):
        day = calendar_start + timedelta(days=offset)
        matches_for_day = calendar_map.get(day, [])
        calendar_days.append(
            {
                "day": day,
                "weekday": day.strftime("%a"),  # Nombre corto del día (ej: Mon, Tue, Wed...)
                "matches": matches_for_day,
                "count": len(matches_for_day),  # Cantidad de partidos ese día
            }
        )

    # 5. RENDIMIENTO GLOBAL DE LOS JUGADORES (Estadísticas acumuladas)
    # Trae los jugadores del equipo precargando sus estadísticas (prefetch_related) para evitar el problema de consultas N+1
    players = team.players.prefetch_related("stats").order_by("nickname")
    player_rows = []
    for player in players:
        # Filtra las estadísticas de partidas completadas del jugador actual
        stats = list(player.stats.filter(match__result__in=decided_results))
        total_kills = sum(stat.kills for stat in stats)
        total_deaths = sum(stat.deaths for stat in stats)
        total_assists = sum(stat.assists for stat in stats)
        maps_played = len(stats)
        # Cuenta en cuántas de esas estadísticas su equipo obtuvo la victoria
        wins_by_player = sum(1 for stat in stats if stat.match.result == Match.ResultType.WIN)
        
        # Cálculo matemático del K/D Ratio protegiendo el sistema de divisiones por cero
        kd_ratio = round(total_kills / total_deaths, 2) if total_deaths else float(total_kills) if total_kills else 0.0
        # Cálculo del Winrate personal del jugador
        winrate = round((wins_by_player / maps_played) * 100, 1) if maps_played else 0.0

        player_rows.append(
            {
                "id": player.id,
                "nickname": player.nickname,
                "maps_played": maps_played,
                "total_kills": total_kills,
                "total_deaths": total_deaths,
                "total_assists": total_assists,
                "kd_ratio": kd_ratio,
                "winrate": winrate,
            }
        )

    # Ordena la tabla de posiciones de jugadores: primero por K/D, luego por Winrate y finalmente por Kills totales
    player_rows.sort(key=lambda item: (item["kd_ratio"], item["winrate"], item["total_kills"]), reverse=True)

    # 6. ANALÍTICA DE RENDIMIENTO POR MAPA DE VALORANT
    # Realiza una consulta agrupada directamente en la base de datos usando .values() y .annotate()
    map_queryset = (
        PlayerMatchStats.objects.filter(player__team=team, match__result__in=decided_results)
        .values("match__map_name")  # Agrupa las filas por el nombre del mapa del partido
        .annotate(
            total_played=Count("match", distinct=True),  # Mapas únicos jugados
            wins=Count("match", filter=Q(match__result=Match.ResultType.WIN), distinct=True),  # Mapas ganados
            total_kills=Sum("kills"),
            total_deaths=Sum("deaths"),
            total_assists=Sum("assists"),
        )
        .order_by("match__map_name")
    )

    # Formatea los resultados agregados de los mapas para el contexto del HTML
    map_rows = []
    for row in map_queryset:
        total_played = row["total_played"] or 0
        total_kills = row["total_kills"] or 0
        total_deaths = row["total_deaths"] or 0
        map_rows.append(
            {
                "map_name": row.get("match__map_name") or "Sin mapa",
                "total_played": total_played,
                "wins": row["wins"] or 0,
                "winrate": round(((row["wins"] or 0) / total_played) * 100, 1) if total_played else 0.0,
                "total_kills": total_kills,
                "total_deaths": total_deaths,
                "total_assists": row["total_assists"] or 0,
                "kd_ratio": round(total_kills / total_deaths, 2) if total_deaths else float(total_kills) if total_kills else 0.0,
            }
        )

    # Ordena los mapas poniendo arriba los más jugados, con mejor winrate o mejor K/D
    map_rows.sort(key=lambda item: (item["total_played"], item["winrate"], item["kd_ratio"]), reverse=True)

    # 7. FILTRO AVANZADO: Estadísticas individuales dentro de un mapa específico
    map_player_stats = []
    if selected_map:
        # Si el usuario hace clic en un mapa, calcula el rendimiento detallado de cada jugador en ese mapa concreto
        map_player_stats = list(
            PlayerMatchStats.objects.filter(
                player__team=team,
                match__result__in=decided_results,
                match__map_name=selected_map,
            )
            .values("player__nickname")
            .annotate(
                nickname=F("player__nickname"),  # Alias del campo agrupado
                total_kills=Sum("kills"),
                total_deaths=Sum("deaths"),
                total_assists=Sum("assists"),
                total_played=Count("id"),
                wins=Count("id", filter=Q(match__result=Match.ResultType.WIN)),
            )
            .values("nickname", "total_kills", "total_deaths", "total_assists", "total_played", "wins")
            .order_by("-total_kills", "nickname")
        )
        # Calcula los porcentajes para el desglose del mapa seleccionado
        for row in map_player_stats:
            total_played = row["total_played"] or 0
            total_kills = row["total_kills"] or 0
            total_deaths = row["total_deaths"] or 0
            wins_for_player = row["wins"] or 0
            row["kd_ratio"] = round(total_kills / total_deaths, 2) if total_deaths else float(total_kills) if total_kills else 0.0
            row["winrate"] = round((wins_for_player / total_played) * 100, 1) if total_played else 0.0

    # 8. ANALÍTICA DE RENDIMIENTO POR AGENTE DE VALORANT
    # Agrupa y procesa las estadísticas según los agentes seleccionados por los jugadores
    agent_queryset = (
        PlayerMatchStats.objects.filter(player__team=team, match__result__in=decided_results)
        .exclude(agent_name="")  # Ignora registros que no tengan el agente especificado
        .values("agent_name")  # Agrupa por nombre de agente (Jett, Reyna, Omen, etc.)
        .annotate(
            total_played=Count("id"),
            wins=Count("id", filter=Q(match__result=Match.ResultType.WIN)),
            total_kills=Sum("kills"),
            total_deaths=Sum("deaths"),
            total_assists=Sum("assists"),
        )
        .order_by("-total_played", "agent_name")
    )

    # Estructura la información de los agentes para enviarla a los gráficos/tablas del Frontend
    agent_rows = []
    for row in agent_queryset:
        total_played = row["total_played"] or 0
        total_kills = row["total_kills"] or 0
        total_deaths = row["total_deaths"] or 0
        agent_rows.append(
            {
                "agent_name": row["agent_name"] or "Sin agente",
                "total_played": total_played,
                "wins": row["wins"] or 0,
                "winrate": round(((row["wins"] or 0) / total_played) * 100, 1) if total_played else 0.0,
                "total_kills": total_kills,
                "total_deaths": total_deaths,
                "total_assists": row["total_assists"] or 0,
                "kd_ratio": round(total_kills / total_deaths, 2) if total_deaths else float(total_kills) if total_kills else 0.0,
            }
        )

    agent_rows.sort(key=lambda item: (item["total_played"], item["winrate"], item["kd_ratio"]), reverse=True)

    # 9. ASIGNACIÓN DEL AGENTE FAVORITO POR JUGADOR
    # Para cada fila de jugador calculada en el paso 5, busca cuál es su agente más utilizado
    for row in player_rows:
        player_stats = list(
            PlayerMatchStats.objects.filter(player_id=row["id"], match__result__in=decided_results)
            .exclude(agent_name="")
            .values("agent_name")
            .annotate(uses=Count("id"))  # Cuenta cuántas veces usó cada agente
            .order_by("-uses", "agent_name")  # El primero de la lista será el que más usó
        )
        # Si tiene partidas registradas guarda el nombre de su "Main Agent", si no, pone un guion
        row["favorite_agent"] = player_stats[0]["agent_name"] if player_stats else "-"

    # 10. LÓGICA DE EVOLUCIÓN TEMPORAL (Historial de Winrate)
    # Sirve para trazar la línea de tendencia de rendimiento del equipo a lo largo del tiempo
    evolution_rows = []
    cumulative_wins = 0
    # Obtiene todos los partidos jugados ordenados cronológicamente desde el más antiguo al más nuevo
    chronological_matches = decided_matches.select_related("tournament").order_by("date")
    for index, match in enumerate(chronological_matches, start=1):
        if match.result == Match.ResultType.WIN:
            cumulative_wins += 1  # Incrementa el contador acumulativo de victorias
        
        # Guarda el estado y calcula el porcentaje de victorias acumulado hasta este partido exacto
        evolution_rows.append(
            {
                "index": index,
                "date": match.date,
                "opponent_name": match.opponent_name,
                "result": match.result,
                "cumulative_winrate": round((cumulative_wins / index) * 100, 1),
            }
        )

    # 11. ACTUALIZACIÓN FINAL DEL CONTEXTO Y RENDERIZADO
    # Inserta todos los sets de datos analíticos procesados dentro del diccionario de contexto base
    context.update(
        {
            "team_summary": {
                "total_matches": total_matches,
                "wins": wins,
                "losses": losses,
                "winrate": round((wins / decided_count) * 100, 1) if decided_count else 0.0,
                "scrims_count": scrims_count,
                "players_count": team.players.count(),
                "pending_count": team.matches.filter(result=Match.ResultType.PENDING).count(),
            },
            "recent_scrims": scrim_matches,
            "pending_matches": pending_matches,
            "calendar_days": calendar_days,
            "player_rows": player_rows,
            "map_rows": map_rows,
            "agent_rows": agent_rows,
            "evolution_rows": evolution_rows[-10:],  # Envía solo los últimos 10 registros para no sobrecargar los gráficos
            "map_player_stats": map_player_stats,
        }
    )

    # Envía los datos procesados a la plantilla HTML y la muestra en pantalla
    return render(request, "dashboard/home.html", context)