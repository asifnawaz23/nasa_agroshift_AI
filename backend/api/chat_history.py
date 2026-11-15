"""Saved chat history for logged-in users.

- POST /api/chat/ calls save_exchange() to store each question + answer.
- GET    /api/chat/conversations/        -> the user's conversations (newest first)
- GET    /api/chat/conversations/<id>/   -> one conversation with all its messages
- DELETE /api/chat/conversations/<id>/   -> delete it
All need the header  Authorization: Token <token>.  Users only ever see their own chats.
"""
from django.db import transaction
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ChatConversation, ChatMessage

TITLE_LENGTH = 60


def user_from_token(request):
    """The logged-in user for a plain Django view (the chat endpoint), or None.

    Reads 'Authorization: Token <key>'. A missing or wrong token just means "not logged
    in" — the chat still answers, it simply isn't saved.
    """
    header = request.META.get("HTTP_AUTHORIZATION", "")
    parts = header.split()
    if len(parts) != 2 or parts[0].lower() != "token":
        return None
    token = Token.objects.select_related("user").filter(key=parts[1]).first()
    if token is None or not token.user.is_active:
        return None
    return token.user


def _title_from(question):
    text = " ".join(question.split())
    return text if len(text) <= TITLE_LENGTH else text[: TITLE_LENGTH - 1].rstrip() + "…"


def save_exchange(user, conversation_id, question, reply, lang):
    """Store one question + answer. Returns the conversation id (new or existing).

    An unknown id, or one that belongs to someone else, starts a new conversation
    instead of failing, so a farmer never loses an answer.
    """
    with transaction.atomic():
        conversation = None
        if conversation_id:
            conversation = ChatConversation.objects.filter(id=conversation_id, user=user).first()
        if conversation is None:
            conversation = ChatConversation.objects.create(user=user, title=_title_from(question))

        ChatMessage.objects.bulk_create([
            ChatMessage(conversation=conversation, role="user", content=question, lang=lang),
            ChatMessage(conversation=conversation, role="assistant", content=reply, lang=lang),
        ])
        conversation.save(update_fields=["updated_at"])  # move it to the top of the list
    return conversation.id


def _conversation_summary(c):
    return {
        "id": c.id,
        "title": c.title,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
        "message_count": getattr(c, "message_count", None),
    }


class ConversationListView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Count

        conversations = (
            ChatConversation.objects.filter(user=request.user)
            .annotate(message_count=Count("messages"))[:50]
        )
        return Response({
            "status": "success",
            "results": [_conversation_summary(c) for c in conversations],
        })


class ConversationDetailView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def _get(self, request, pk):
        return ChatConversation.objects.filter(id=pk, user=request.user).first()

    def get(self, request, pk):
        conversation = self._get(request, pk)
        if conversation is None:
            return Response(
                {"status": "error", "message": "Conversation not found.", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({
            "status": "success",
            "conversation": _conversation_summary(conversation),
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "lang": m.lang,
                    "created_at": m.created_at.isoformat(),
                }
                for m in conversation.messages.all()
            ],
        })

    def delete(self, request, pk):
        conversation = self._get(request, pk)
        if conversation is None:
            return Response(
                {"status": "error", "message": "Conversation not found.", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        conversation.delete()
        return Response({"status": "success", "message": "Conversation deleted."})
