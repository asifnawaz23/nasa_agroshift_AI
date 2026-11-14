
from django.urls import path

from .views import analyze, health_check

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("analyze/", analyze, name="analyze"),
]
