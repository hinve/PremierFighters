from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from dashboard.views import home
from teams.views import team_list, team_detail, team_create, team_update, team_delete, team_stats
from players.views import player_list, player_detail, player_create, player_update, player_delete
from matches.views import match_list, match_detail, match_update, match_delete, match_create_with_stats, match_add_player
from stats.views import mapresult_list, mapresult_detail, mapresult_create, mapresult_update, mapresult_delete

urlpatterns = [
    path("admin/", admin.site.urls),
    path("docs/", include("django.contrib.admindocs.urls")),
    path("login/", auth_views.LoginView.as_view(template_name="auth/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", home, name="home"),

    path("teams/", team_list, name="team_list"),
    path("teams/create/", team_create, name="team_create"),
    path("teams/<int:team_id>/", team_detail, name="team_detail"),
    path("teams/<int:team_id>/stats/", team_stats, name="team_stats"),
    path("teams/<int:team_id>/edit/", team_update, name="team_update"),
    path("teams/<int:team_id>/delete/", team_delete, name="team_delete"),

    path("players/", player_list, name="player_list"),
    path("players/create/", player_create, name="player_create"),
    path("players/<int:player_id>/", player_detail, name="player_detail"),
    path("players/<int:player_id>/edit/", player_update, name="player_update"),
    path("players/<int:player_id>/delete/", player_delete, name="player_delete"),
    
    path("matches/", match_list, name="match_list"),
    path("matches/create/", match_create_with_stats, name="match_create"),
    path("matches/<int:match_id>/", match_detail, name="match_detail"),
    path("matches/<int:match_id>/edit/", match_update, name="match_update"),
    path("matches/<int:match_id>/delete/", match_delete, name="match_delete"),  
    path("matches/<int:match_id>/add_player/", match_add_player, name="match_add_player"),

    path("stats/", mapresult_list, name="mapresult_list"),
    path("stats/create/", mapresult_create, name="mapresult_create"),
    path("stats/<int:stat_id>/", mapresult_detail, name="mapresult_detail"),
    path("stats/<int:stat_id>/edit/", mapresult_update, name="mapresult_update"),
    path("stats/<int:stat_id>/delete/", mapresult_delete, name="mapresult_delete"),
]