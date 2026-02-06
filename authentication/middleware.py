from asgiref.sync import sync_to_async


class XSessionTokenMiddleware:
    """
    Middleware to authenticate users via X-Session-Token header for ASGI.
    This is designed to work within or alongside AuthMiddlewareStack.
    It checks for the 'x-session-token' header and, if present and the user
    is not already authenticated (e.g. via cookie), attempts to authenticate
    using django-allauth's headless session kit.
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # Only handle HTTP or WebSocket scopes
        if scope["type"] not in ("http", "websocket"):
            return await self.inner(scope, receive, send)

        # Check if user is already authenticated by AuthMiddlewareStack via cookie
        # AuthMiddlewareStack ensures 'user' is in scope (even if AnonymousUser)
        user = scope.get("user")
        if user and user.is_authenticated:
            return await self.inner(scope, receive, send)

        # Look for X-Session-Token header
        # Headers are list of tuples [(b'name', b'value')], convert to dict for lookup
        headers = dict(scope.get("headers", []))
        # Header keys are lowercased by the ASGI server
        session_token = headers.get(b"x-session-token", b"").decode("utf-8")

        if session_token:
            try:
                # Lazy import to avoid App Registry access during ASGI initialization
                from allauth.headless.internal.sessionkit import (
                    authenticate_by_x_session_token,
                )

                # Authenticate using allauth's internal sessionkit
                # sync_to_async is needed as it performs database operations
                auth_result = await sync_to_async(authenticate_by_x_session_token)(
                    session_token
                )
                if auth_result:
                    user, _ = auth_result
                    scope["user"] = user
            except Exception:
                # Silently fail on auth errors and let the request proceed as anonymous
                # or let the consumer handle the lack of a user.
                pass

        return await self.inner(scope, receive, send)
