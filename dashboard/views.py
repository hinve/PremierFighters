from datetime import timedelta
from typing import Any, cast

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Q, Sum
from django.shortcuts import render
from django.utils import timezone

from matches.models import Match
from stats.models import PlayerMatchStats
from teams.models import Team
from users.permissions import get_user_team


def _get_accessible_teams(user):
    if getattr(user, "role", "").lower() == "admin":
        return Team.objects.all().order_by("name")

    team = get_user_team(user)
    if team:
        return Team.objects.filter(id=team.id)
    return Team.objects.none()

@login_required
def home(request):
    teams = _get_accessible_teams(request.user)
    selected_team = None
    selected_team_id = request.GET.get("team_id") or request.GET.get("team")
    selected_map = request.GET.get("selected_map") or ""

    if selected_team_id:
        selected_team = teams.filter(id=selected_team_id).first()
        if not selected_team:
            messages.warning(request, "Selecciona un equipo válido para ver sus reportes.")
    elif teams.count() == 1:
        selected_team = teams.first()

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

    if not selected_team:
        return render(request, "dashboard/home.html", context)

    team = cast(Any, selected_team)
    decided_results = [Match.ResultType.WIN, Match.ResultType.LOSS]

    now = timezone.now()
    today = timezone.localdate()

    decided_matches = team.matches.filter(result__in=decided_results)
    total_matches = decided_matches.count()
    wins = decided_matches.filter(result=Match.ResultType.WIN).count()
    losses = total_matches - wins
    decided_count = decided_matches.count()
    scrims_count = decided_matches.filter(match_type=Match.MatchType.SCRIM).count()
    scrim_matches = (
        decided_matches.filter(match_type=Match.MatchType.SCRIM)
        .select_related("tournament")
        .order_by("-date")[:5]
    )
    pending_matches = team.matches.filter(result=Match.ResultType.PENDING).select_related("tournament").order_by("date")[:5]

    calendar_start = today
    calendar_end = today + timedelta(days=6)
    calendar_matches = team.matches.filter(date__date__range=(calendar_start, calendar_end)).order_by("date")
    calendar_map = {calendar_start + timedelta(days=offset): [] for offset in range(7)}
    for match in calendar_matches:
        match_day = timezone.localdate(match.date)
        if match_day in calendar_map:
            calendar_map[match_day].append(match)

    calendar_days = []
    for offset in range(7):
        day = calendar_start + timedelta(days=offset)
        matches_for_day = calendar_map.get(day, [])
        calendar_days.append(
            {
                "day": day,
                "weekday": day.strftime("%a"),
                "matches": matches_for_day,
                "count": len(matches_for_day),
            }
        )

    players = team.players.prefetch_related("stats").order_by("nickname")
    player_rows = []
    for player in players:
        stats = list(player.stats.filter(match__result__in=decided_results))
        total_kills = sum(stat.kills for stat in stats)
        total_deaths = sum(stat.deaths for stat in stats)
        total_assists = sum(stat.assists for stat in stats)
        maps_played = len(stats)
        wins_by_player = sum(1 for stat in stats if stat.match.result == Match.ResultType.WIN)
        kd_ratio = round(total_kills / total_deaths, 2) if total_deaths else float(total_kills) if total_kills else 0.0
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

    player_rows.sort(key=lambda item: (item["kd_ratio"], item["winrate"], item["total_kills"]), reverse=True)

    # Aggregate by Match.map_name instead of PlayerMatchStats.map_name
    map_queryset = (
        PlayerMatchStats.objects.filter(player__team=team, match__result__in=decided_results)
        .values("match__map_name")
        .annotate(
            total_played=Count("match", distinct=True),
            wins=Count("match", filter=Q(match__result=Match.ResultType.WIN), distinct=True),
            total_kills=Sum("kills"),
            total_deaths=Sum("deaths"),
            total_assists=Sum("assists"),
        )
        .order_by("match__map_name")
    )

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

    map_rows.sort(key=lambda item: (item["total_played"], item["winrate"], item["kd_ratio"]), reverse=True)

    map_player_stats = []
    if selected_map:
        map_player_stats = list(
            PlayerMatchStats.objects.filter(
                player__team=team,
                match__result__in=decided_results,
                match__map_name=selected_map,
            )
            .values("player__nickname")
            .annotate(
                nickname=F("player__nickname"),
                total_kills=Sum("kills"),
                total_deaths=Sum("deaths"),
                total_assists=Sum("assists"),
                total_played=Count("id"),
                wins=Count("id", filter=Q(match__result=Match.ResultType.WIN)),
            )
            .values("nickname", "total_kills", "total_deaths", "total_assists", "total_played", "wins")
            .order_by("-total_kills", "nickname")
        )
        for row in map_player_stats:
            total_played = row["total_played"] or 0
            total_kills = row["total_kills"] or 0
            total_deaths = row["total_deaths"] or 0
            wins_for_player = row["wins"] or 0
            row["kd_ratio"] = round(total_kills / total_deaths, 2) if total_deaths else float(total_kills) if total_kills else 0.0
            row["winrate"] = round((wins_for_player / total_played) * 100, 1) if total_played else 0.0

    agent_queryset = (
        PlayerMatchStats.objects.filter(player__team=team, match__result__in=decided_results)
        .exclude(agent_name="")
        .values("agent_name")
        .annotate(
            total_played=Count("id"),
            wins=Count("id", filter=Q(match__result=Match.ResultType.WIN)),
            total_kills=Sum("kills"),
            total_deaths=Sum("deaths"),
            total_assists=Sum("assists"),
        )
        .order_by("-total_played", "agent_name")
    )

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

    for row in player_rows:
        player_stats = list(
            PlayerMatchStats.objects.filter(player_id=row["id"], match__result__in=decided_results)
            .exclude(agent_name="")
            .values("agent_name")
            .annotate(uses=Count("id"))
            .order_by("-uses", "agent_name")
        )
        row["favorite_agent"] = player_stats[0]["agent_name"] if player_stats else "-"

    evolution_rows = []
    cumulative_wins = 0
    chronological_matches = decided_matches.select_related("tournament").order_by("date")
    for index, match in enumerate(chronological_matches, start=1):
        if match.result == Match.ResultType.WIN:
            cumulative_wins += 1
        evolution_rows.append(
            {
                "index": index,
                "date": match.date,
                "opponent_name": match.opponent_name,
                "result": match.result,
                "cumulative_winrate": round((cumulative_wins / index) * 100, 1),
            }
        )

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
            "evolution_rows": evolution_rows[-10:],
            "map_player_stats": map_player_stats,
        }
    )

    return render(request, "dashboard/home.html", context)
