def get_client_group_name(user_id: str | int) -> str:
    """
    Returns the channel group name used for broadcasting events to a user's clients.

    Format: "user_{user_id}_clients"
    Usage:
        - ClientConsumer: Joins this group to receive updates.
        - Handlers: Sends messages to this group to notify the subscribed clients.
    """
    return f"user_{user_id}_clients"


def get_agent_group_name(agent_key: str) -> str:
    """
    Returns the channel group name used for sending control commands to the
    specific agent.

    Format: "agent_{agent_key}"
    Usage:
        - AgentConsumer: Joins this group to receive commands (e.g., force_disconnect).
        - Internals: Sends command messages to this group.
    """
    return f"agent_{agent_key}"
