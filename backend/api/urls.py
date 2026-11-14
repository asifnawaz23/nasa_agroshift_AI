
from django.urls import path

from .views import (
    analyze,
    chat,
    crops,
    explain,
    health_check,
    locations,
)

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("locations/", locations, name="locations"),
    path("crops/", crops, name="crops"),
    path("analyze/", analyze, name="analyze"),
    path("explain/", explain, name="explain"),
    path("chat/", chat, name="chat"),
]
