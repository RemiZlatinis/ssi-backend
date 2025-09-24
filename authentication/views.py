from typing import Any, Dict, Optional

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from django.http import HttpRequest


class CustomGoogleOAuth2Client(OAuth2Client):
    """This custom is a hotfix for removing the incompatible `scope` argument."""

    def __init__(
        self,
        request: HttpRequest,
        consumer_key: str,
        consumer_secret: str,
        access_token_method: str,
        access_token_url: str,
        callback_url: str,
        _scope: Any,  # Hotfix incompatible django-allauth and dj-rest-auth
        scope_delimiter: str = " ",
        headers: Optional[Dict[str, str]] = None,
        basic_auth: bool = False,
    ) -> None:
        super().__init__(
            request,
            consumer_key,
            consumer_secret,
            access_token_method,
            access_token_url,
            callback_url,
            scope_delimiter,
            headers,
            basic_auth,
        )


class GoogleLogin(SocialLoginView):
    """Custom Google login view for dj-rest-auth.

    This view handles the Google OAuth2 authentication process for dj-rest-auth.
    """

    adapter_class = GoogleOAuth2Adapter
    callback_url = "https://service-status-indicator.firebaseapp.com/__/auth/handler"
    client_class = CustomGoogleOAuth2Client
