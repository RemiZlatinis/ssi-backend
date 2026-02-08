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
    Returns the base channel name for a user's SSE connections.

    This provides a deterministic prefix for all connections from a user.
    Each connection should append a unique suffix (e.g., UUID) to create
    the final channel name: f"{base_channel}_{unique_suffix}"

    This hybrid approach ensures:
    - All clients receive messages (unique channels per connection)
    - Debuggable channel names (user ID in prefix)
    - No race conditions in channels_redis

    Format: "sse_user_{user_id}"
    Example final channel: "sse_user_2_a1b2c3d4"
    """
    return f"sse_user_{user_id}"
