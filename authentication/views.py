"""
Authentication views for the SSI backend.

This module provides CSRF token endpoint for headless web clients,
as Django templates are not used in this API-only architecture.
"""

from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(ensure_csrf_cookie, name="get")
class CsrfTokenView(View):
    """
    Provides CSRF token for headless web clients.

    Since Django is used headlessly (no templates), this endpoint allows
    SPAs to fetch the CSRF token required for POST/PUT/DELETE requests.
    The @ensure_csrf_cookie decorator ensures the csrftoken cookie is set.

    GET /api/auth/csrf/

    Response:
        {
            "csrfToken": "the-csrf-token-value"
        }
    """

    def get(self, request):
        """
        Return the CSRF token.

        The ensure_csrf_cookie decorator ensures the csrftoken cookie
        is included in the response, which is then read by JavaScript
        and sent back as X-CSRFToken header on mutating requests.
        """
        csrf_token = get_token(request)
        return JsonResponse({"csrfToken": csrf_token})
