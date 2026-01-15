"""
Custom Headless Adapter for django-allauth.

This adapter customizes the user serialization to include the profile picture
from the user's linked social account (e.g., Google OAuth).
"""

from typing import Any

from allauth.headless.adapter import DefaultHeadlessAdapter
from django.contrib.auth.models import AbstractUser


class CustomHeadlessAdapter(DefaultHeadlessAdapter):
    """
    Extends the default headless adapter to include the users' profile picture
    in the serialization.
    """

    def serialize_user(self, user: AbstractUser) -> dict[str, Any]:
        """
        Serialize user data with additional profile picture field.

        The profile picture is fetched from the user's social account
        (Google, etc.) if available.
        """
        data = super().serialize_user(user)

        # Add profile picture from social account
        try:
            from allauth.socialaccount.models import SocialAccount

            social = SocialAccount.objects.filter(user=user).first()
            data["picture"] = social.get_avatar_url() if social else None
        except Exception:
            data["picture"] = None

        return data
