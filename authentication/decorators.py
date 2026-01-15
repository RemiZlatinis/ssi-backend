"""
Authentication decorators for django-allauth headless integration.
"""

from functools import wraps

from allauth.headless.internal.sessionkit import authenticate_by_x_session_token
from asgiref.sync import sync_to_async
from django.http import HttpRequest


def authenticate_headless(view_func):
    """
    Authenticate async views using X-Session-Token header (django-allauth headless).

    This decorator extracts the X-Session-Token from request headers and populates
    request.user and request.session using the same authentication flow as DRF
    XSessionTokenAuthentication.

    Usage:
        @authenticate_headless
        async def my_view(request):
            if request.user.is_authenticated:
                # User is authenticated
                pass
    """

    @wraps(view_func)
    async def wrapper(request: HttpRequest, *args, **kwargs):
        session_token = request.headers.get("X-Session-Token")

        if session_token:
            auth_result = await sync_to_async(authenticate_by_x_session_token)(
                session_token
            )
            if auth_result is not None:
                user, session = auth_result
                request.user = user
                request.session = session

        return await view_func(request, *args, **kwargs)

    return wrapper


def require_headless_auth(view_func):
    """
    Require authentication for async views using X-Session-Token.

    Returns 401 Unauthorized if user is not authenticated.

    Usage:
        @require_headless_auth
        async def my_protected_view(request):
            # User is guaranteed to be authenticated here
            pass
    """

    @wraps(view_func)
    async def wrapper(request: HttpRequest, *args, **kwargs):
        from django.http import JsonResponse

        session_token = request.headers.get("X-Session-Token")

        if session_token:
            auth_result = await sync_to_async(authenticate_by_x_session_token)(
                session_token
            )
            if auth_result is not None:
                user, session = auth_result
                request.user = user
                request.session = session

        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)

        return await view_func(request, *args, **kwargs)

    return wrapper
