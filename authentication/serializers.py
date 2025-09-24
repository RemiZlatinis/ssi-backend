from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User as DjangoUser
from rest_framework import serializers

User = get_user_model()


class CustomUserDetailsSerializer(serializers.ModelSerializer):
    """
    Custom user model serializer to include the social account's profile picture.
    """

    picture = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",  # Use 'id' instead of 'pk'
            "username",
            "email",
            "first_name",
            "last_name",
            "picture",  # Add the 'picture' field
        )
        read_only_fields = fields

    def get_picture(self, user: DjangoUser) -> str | None:
        """
        Returns the profile picture URL from the user's social account (if available).
        """
        try:
            # We are assuming one social account per user for simplicity
            # This must change if more OAuth providers added in the future
            social_account = SocialAccount.objects.get(user=user)
            return social_account.get_avatar_url() or None
        except SocialAccount.DoesNotExist:
            return None
