def get_client_ip(scope_or_request):
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
    # Check if it's a Django request object (has a 'META' attribute)
    if hasattr(scope_or_request, "META"):
        x_forwarded_for = scope_or_request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return scope_or_request.META.get("REMOTE_ADDR")

    # Check if it's a Channels scope object (has a 'headers' attribute)
    if "headers" in scope_or_request:
        headers = dict(scope_or_request.get("headers", []))
        x_forwarded_for = headers.get(b"x-forwarded-for")
        if x_forwarded_for:
            return x_forwarded_for.decode("utf-8").split(",")[0].strip()
        return scope_or_request.get("client", (None, None))[0]

    return None
