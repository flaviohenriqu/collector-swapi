from django.urls import path

from . import views

app_name = "swapi"

urlpatterns = [
    path("", views.index, name="index"),
    path("fetch/", views.create_collection, name="fetch"),
    path("list/<uuid:collection_uid>/", views.list_csv, name="list"),
    path("value/<uuid:collection_uid>/", views.value_count, name="value"),
]
