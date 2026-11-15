
from django.urls import path

from .chat_history import ConversationDetailView, ConversationListView

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
    path("chat/conversations/", ConversationListView.as_view(), name="chat-conversations"),
    path("chat/conversations/<int:pk>/", ConversationDetailView.as_view(), name="chat-conversation"),
]
