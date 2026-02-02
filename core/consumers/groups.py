def get_client_group_name(user_id: str | int) -> str:
    """
    Returns the channel group name used for broadcasting events to a user's clients.

    Format: "user_{user_id}_clients"
    Usage:
        - ClientConsumer: Joins this group to receive updates.
        - Handlers: Sends messages to this group to notify the subscribed clients.
    """
    return f"user_{user_id}_clients"
