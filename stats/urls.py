from django.urls import path

from .views import mapresult_list, mapresult_detail, mapresult_create, mapresult_update, mapresult_delete

urlpatterns = [
    path("", mapresult_list, name="mapresult_list"),
    path("create/", mapresult_create, name="mapresult_create"),
    path("<int:stat_id>/", mapresult_detail, name="mapresult_detail"),
    path("<int:stat_id>/edit/", mapresult_update, name="mapresult_update"),
    path("<int:stat_id>/delete/", mapresult_delete, name="mapresult_delete"),
]