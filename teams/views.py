from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from users.permissions import ensure_can_manage_team, get_user_team

from .forms import TeamForm
from .models import Team


@login_required
def team_list(request):
    if request.user.role == "admin":
        teams = Team.objects.all()
    else:
        team = get_user_team(request.user)
        teams = Team.objects.filter(id=team.id) if team else Team.objects.none()
    return render(request, "teams/team_list.html", {"teams": teams})


@login_required
def team_detail(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    # Para este bloque mantenemos la misma regla de acceso que venías usando
    return render(request, "teams/team_detail.html", {"team": team})


@login_required
def team_create(request):
    # Si no es admin y ya tiene equipo asignado, no permitimos crear otro
    if request.user.role != "admin":
        my_team = get_user_team(request.user)
        if my_team:
            return redirect("team_detail", team_id=my_team.id)

    if request.method == "POST":
        form = TeamForm(request.POST)
        if form.is_valid():
            team = form.save()

            # Si quien crea no es admin, lo atamos como coach/manager de ese equipo
            if request.user.role == "coach" and not team.coach:
                team.coach = request.user
                team.save()
            elif request.user.role == "manager" and not team.manager:
                team.manager = request.user
                team.save()

            return redirect("team_detail", team_id=team.id)
    else:
        form = TeamForm()

    return render(request, "teams/team_form.html", {"form": form, "mode": "create"})


@login_required
def team_update(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    try:
        ensure_can_manage_team(request.user, team)
    except PermissionDenied:
        messages.error(request, "No tienes permisos para editar este equipo.")
        return redirect("team_detail", team_id=team.id)  # type: ignore

    if request.method == "POST":
        form = TeamForm(request.POST, instance=team)
        if form.is_valid():
            form.save()
            return redirect("team_detail", team_id=team.pk)
    else:
        form = TeamForm(instance=team)

    return render(request, "teams/team_form.html", {"form": form, "team": team, "mode": "edit"})


@login_required
def team_delete(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    try:
        ensure_can_manage_team(request.user, team)
    except PermissionDenied:
        messages.error(request, "No tienes permisos para eliminar este equipo.")
        return redirect("team_detail", team_id=team.id)  # type: ignore

    if request.method == "POST":
        team.delete()
        return redirect("team_list")

    return render(request, "teams/team_confirm_delete.html", {"team": team})