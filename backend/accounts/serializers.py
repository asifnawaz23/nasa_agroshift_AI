from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

User = get_user_model()


def profile_picture_url(user, request=None):
    """Public URL of the user's profile picture, or None if they have not uploaded one."""
    profile = getattr(user, "userprofile", None)
    picture = getattr(profile, "profile_picture", None)
    if not picture:
        return None
    url = picture.url
    # Cloudinary gives a full https:// URL; the local fallback gives /media/... (make it absolute)
    if request is not None and url.startswith("/"):
        url = request.build_absolute_uri(url)
    return url


def user_payload(user, request=None):
    """The user object returned to the frontend (never includes the password)."""
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.get_full_name(),
        "date_joined": user.date_joined.isoformat(),
        "profile_picture": profile_picture_url(user, request),
    }


MAX_PICTURE_MB = 5
ALLOWED_PICTURE_TYPES = {"image/jpeg", "image/png", "image/webp"}


class ProfilePictureSerializer(serializers.Serializer):
    # ImageField checks with Pillow that the file really is an image
    profile_picture = serializers.ImageField()

    def validate_profile_picture(self, image):
        if image.size > MAX_PICTURE_MB * 1024 * 1024:
            raise serializers.ValidationError(f"Image must be {MAX_PICTURE_MB} MB or smaller.")
        if getattr(image, "content_type", None) not in ALLOWED_PICTURE_TYPES:
            raise serializers.ValidationError("Use a JPG, PNG or WebP image.")
        return image


def _split_name(full_name):
    first, _, last = full_name.strip().partition(" ")
    return first, last.strip()


class SignupSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    confirm_password = serializers.CharField(
        write_only=True, trim_whitespace=False, required=False
    )

    def validate_email(self, value):
        email = value.strip().lower()
        if (
            User.objects.filter(username__iexact=email).exists()
            or User.objects.filter(email__iexact=email).exists()
        ):
            raise serializers.ValidationError(
                "An account with this email already exists."
            )
        return email

    def validate(self, attrs):
        confirm = attrs.pop("confirm_password", None)
        if confirm is not None and confirm != attrs["password"]:
            raise serializers.ValidationError(
                {"confirm_password": ["Passwords do not match."]}
            )

        first, last = _split_name(attrs["full_name"])
        candidate = User(
            username=attrs["email"],
            email=attrs["email"],
            first_name=first,
            last_name=last,
        )
        try:
            # Uses AUTH_PASSWORD_VALIDATORS from settings.py
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})

        return attrs

    def create(self, validated_data):
        first, last = _split_name(validated_data["full_name"])
        # The email is used as the username, so login is by email.
        return User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=first,
            last_name=last,
        )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        return value.strip().lower()