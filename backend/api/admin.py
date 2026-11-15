from django.contrib import admin

from .models import ChatConversation, ChatMessage


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ("role", "content", "lang", "created_at")


@admin.register(ChatConversation)
class ChatConversationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "updated_at")
    search_fields = ("title", "user__email")
    inlines = [ChatMessageInline]
