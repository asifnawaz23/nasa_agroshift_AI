from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import UserProfile
from .serializers import (
    LoginSerializer,
    ProfilePictureSerializer,
    SignupSerializer,
    user_payload,
)


def _error(message, errors=None, http_status=status.HTTP_400_BAD_REQUEST):
    return Response(
        {"status": "error", "message": message, "errors": errors or {}},
        status=http_status,
    )


class SignupView(APIView):
    """POST /api/auth/signup/  ->  creates the account and returns a token."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if not serializer.is_valid():
            return _error("Signup failed.", serializer.errors)

        try:
            with transaction.atomic():
                user = serializer.save()
                token = Token.objects.create(user=user)
        except IntegrityError:
            # Two signups with the same email at the same moment
            return _error(
                "Signup failed.",
                {"email": ["An account with this email already exists."]},
            )

        return Response(
            {
                "status": "success",
                "message": "Account created.",
                "user": user_payload(user, request),
                "token": token.key,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """POST /api/auth/login/  ->  returns the user and their token."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return _error("Login failed.", serializer.errors)

        user = authenticate(
            request,
            username=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return _error(
                "Invalid email or password.",
                http_status=status.HTTP_401_UNAUTHORIZED,
            )

        token, _ = Token.objects.get_or_create(user=user)
        update_last_login(None, user)

        return Response(
            {
                "status": "success",
                "message": "Logged in.",
                "user": user_payload(user, request),
                "token": token.key,
            }
        )


class LogoutView(APIView):
    """POST /api/auth/logout/  (header: Authorization: Token <token>)."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.auth.delete()
        return Response({"status": "success", "message": "Logged out."})


class MeView(APIView):
    """GET /api/auth/me/  (header: Authorization: Token <token>)."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"status": "success", "user": user_payload(request.user, request)})


class ProfilePictureView(APIView):
    """Profile picture (stored on Cloudinary).

    POST   /api/auth/profile-picture/   multipart form, field "profile_picture"  -> updated user
    DELETE /api/auth/profile-picture/                                           -> updated user
    Header: Authorization: Token <token>
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = ProfilePictureSerializer(data=request.data)
        if not serializer.is_valid():
            return _error("Upload failed.", serializer.errors)

        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        old = profile.profile_picture
        if old:
            old.delete(save=False)  # remove the previous image from Cloudinary

        profile.profile_picture = serializer.validated_data["profile_picture"]
        profile.save()

        return Response({
            "status": "success",
            "message": "Profile picture updated.",
            "user": user_payload(request.user, request),
        })

    def delete(self, request):
        profile = UserProfile.objects.filter(user=request.user).first()
        if profile and profile.profile_picture:
            profile.profile_picture.delete(save=False)
            profile.profile_picture = ""
            profile.save()

        return Response({
            "status": "success",
            "message": "Profile picture removed.",
            "user": user_payload(request.user, request),
        })