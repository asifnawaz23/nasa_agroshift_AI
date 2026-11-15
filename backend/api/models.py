from django.conf import settings
from django.db import models


class ChatConversation(models.Model):
    """One chat thread with the farm assistant, owned by a logged-in user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_conversations"
    )
    # First question, shortened — shown in the history list
    title = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user} — {self.title}"


class ChatMessage(models.Model):
    """One message in a conversation: the farmer's question or the assistant's answer."""

    ROLE_CHOICES = [("user", "Farmer"), ("assistant", "Assistant")]

    conversation = models.ForeignKey(
        ChatConversation, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    lang = models.CharField(max_length=5, default="en")  # en, ur, sd, pa
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.role}: {self.content[:40]}"
