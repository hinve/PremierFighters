from django.shortcuts import render
from users.permissions import get_user_team
from .models import Match

# Create your views here.
def match_list(request):
    if request.user.role == "admin":
        matches = Match.objects.select_related('team', 'tournament')
    else:
        team = get_user_team(request.user)
        matches = Match.objects.filter(team=team).select_related('team', 'tournament') if team else Match.objects.none()
    return render(request, "matches/match_list.html", {"matches": matches})