def get_client_group_name(user_id: str | int) -> str:
    """
    Returns the channel group name used for broadcasting events to a user's clients.

    Format: "user_{user_id}_clients"
    Usage:
        - ClientConsumer: Joins this group to receive updates.
        - Handlers: Sends messages to this group to notify the subscribed clients.

    Note: Multiple SSE connections from the same user all join this group,
    but they share a single channel name (see get_user_sse_channel_name).
    This prevents race conditions in channels_redis.
    """
    return f"user_{user_id}_clients"


def get_user_sse_channel_name(user_id: str | int) -> str:
    """
    Returns the deterministic channel name for a user's SSE connections.

    All SSE connections from the same user share this channel name,
    which prevents race conditions in channels_redis when multiple
    connections exist simultaneously.

    Format: "sse_user_{user_id}"
    """
    return f"sse_user_{user_id}"
