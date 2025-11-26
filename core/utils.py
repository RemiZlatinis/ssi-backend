from __future__ import annotations

from typing import Any, cast

from django.http import HttpRequest


def get_client_ip(
    scope_or_request: HttpRequest | dict[str, Any],
) -> str | None:
    """
    Get the client's real IP address from a request or a WebSocket scope.

    This function correctly handles the 'X-Forwarded-For' header, which is
    essential when the application is running behind a reverse proxy, load
    balancer, or other gateway.

    Args:
        scope_or_request: A Django request object or a Channels scope dictionary.

    Returns:
        The client's IP address as a string, or None if it cannot be determined.
    """
    # Check if it's a Django request object
    if isinstance(scope_or_request, HttpRequest):
        x_forwarded_for = scope_or_request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return cast(str, x_forwarded_for).split(",")[0].strip()
        return scope_or_request.META.get("REMOTE_ADDR")

    # Check if it's a Channels scope object
    elif isinstance(scope_or_request, dict):
        if "headers" in scope_or_request:
            headers_list = scope_or_request.get("headers", [])
            headers = dict(cast(list[tuple[bytes, bytes]], headers_list))
            x_forwarded_for = headers.get(b"x-forwarded-for")
            if x_forwarded_for:
                return x_forwarded_for.decode("utf-8").split(",")[0].strip()

        # Fallback to client info if available
        client_info = scope_or_request.get("client", (None, None))
        ip_tuple = cast(tuple[str | None, int | None], client_info)
        return ip_tuple[0]

    return None


def get_static_icon_url(icon_name: str) -> str:
    """
    Returns the full public URL for a static icon.
    """
    import os

    from django.conf import settings

    base_url = "http://127.0.0.1:8000"

    if settings.ENVIRONMENT == "production":
        host = os.getenv("HOST")
        if host:
            domain = host.split(",")[0].strip()
            base_url = f"https://{domain}"

    static_url = settings.STATIC_URL.strip("/")
    return f"{base_url}/{static_url}/icons/{icon_name}"
