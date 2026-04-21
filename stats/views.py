from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from users.permissions import get_user_team

from .models import PlayerMatchStats


@login_required
def team_list(request):
    if request.user.role == "admin":
        stats = PlayerMatchStats.objects.select_related("team").all()
    else:
        team = get_user_team(request.user)
        stats = PlayerMatchStats.objects.select_related("team").filter(team=team) if team else PlayerMatchStats.objects.none()

    return render(request, "stats/stats_list.html", {"stats": stats})