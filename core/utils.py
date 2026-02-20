from typing import Any, cast


def get_client_ip(scope: dict[str, Any]) -> str | None:
    """
    Get the client's real IP address from a WebSocket scope.

    This function correctly handles the 'X-Forwarded-For' header, which is
    essential when the application is running behind a reverse proxy, load
    balancer, or other gateway.

    Args:
        scope: A Channels scope dictionary from WebSocket connection.

    Returns:
        The client's IP address as a string, or None if it cannot be determined.
    """
    headers_list = scope.get("headers", [])
    if headers_list:
        headers = dict(cast(list[tuple[bytes, bytes]], headers_list))
        x_forwarded_for = headers.get(b"x-forwarded-for")
        if x_forwarded_for:
            return x_forwarded_for.decode("utf-8").split(",")[0].strip()

    # Fallback to client info if available
    client_info = scope.get("client", (None, None))
    ip_tuple = cast(tuple[str | None, int | None], client_info)
    return ip_tuple[0]
