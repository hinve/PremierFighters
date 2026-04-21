from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from dashboard.views import home
from teams.views import team_list, team_detail, team_create, team_update, team_delete
from players.views import player_list, player_detail, player_create, player_update, player_delete

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(template_name="auth/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", home, name="home"),

    path("teams/", team_list, name="team_list"),
    path("teams/create/", team_create, name="team_create"),
    path("teams/<int:team_id>/", team_detail, name="team_detail"),
    path("teams/<int:team_id>/edit/", team_update, name="team_update"),
    path("teams/<int:team_id>/delete/", team_delete, name="team_delete"),

    path("players/", player_list, name="player_list"),
    path("players/create/", player_create, name="player_create"),
    path("players/<int:player_id>/", player_detail, name="player_detail"),
    path("players/<int:player_id>/edit/", player_update, name="player_update"),
    path("players/<int:player_id>/delete/", player_delete, name="player_delete"),
]