"""
Authentication decorators for django-allauth headless integration.
"""

from functools import wraps

from allauth.headless.internal.sessionkit import authenticate_by_x_session_token
from asgiref.sync import sync_to_async


def sse_require_auth(consumer_handle_func):
    """
    Decorator for AsyncHttpConsumer.handle method to require authentication
    via X-Session-Token.

    If authentication fails, it sends a 401 response and stops execution.
    If successful, it injects the authenticated user into self.scope["user"].
    """

    @wraps(consumer_handle_func)
    async def wrapper(self, body):
        headers = dict(self.scope.get("headers", []))
        session_token = headers.get(b"x-session-token", b"").decode("utf-8")

        user = None
        if session_token:
            auth_result = await sync_to_async(authenticate_by_x_session_token)(
                session_token
            )
            if auth_result:
                user, _ = auth_result

        if not user or not user.is_authenticated:
            await self.send_response(
                401,
                b"Authentication required",
                headers=[
                    (b"Content-Type", b"application/json"),
                ],
            )
            return

        self.scope["user"] = user
        return await consumer_handle_func(self, body)

    return wrapper
