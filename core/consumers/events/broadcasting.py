import logging

from channels.layers import get_channel_layer

from core.consumers.groups import get_client_group_name

from .typing import (
    ClientServiceAddedEvent,
    ClientServiceRemovedEvent,
    ClientServiceStatusUpdateEvent,
    ClientStatusUpdateEvent,
)

logger = logging.getLogger(__name__)


async def broadcast_agent_status_update(
    owner_id: int, event: ClientStatusUpdateEvent
) -> None:
    """
    Helper to broadcast a pre-built agent status update event
    to all connected clients for that agent's owner.
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.debug("Channel layer not configured. Cannot broadcast agent status.")
        return

    user_clients_group_name = get_client_group_name(owner_id)
    await channel_layer.group_send(
        user_clients_group_name,
        {
            "type": "status_update",
            "event": event.model_dump(mode="json"),
        },
    )


async def broadcast_service_added(
    owner_id: int, event: ClientServiceAddedEvent
) -> None:
    """
    Broadcast service added event to clients.
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.debug("Channel layer not configured. Cannot broadcast service added.")
        return

    user_clients_group_name = get_client_group_name(owner_id)
    await channel_layer.group_send(
        user_clients_group_name,
        {
            "type": "service_added",
            "event": event.model_dump(mode="json"),
        },
    )


async def broadcast_service_removed(
    owner_id: int, event: ClientServiceRemovedEvent
) -> None:
    """
    Broadcast service removed event to clients.
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.debug("Channel layer not configured. Cannot broadcast service removed.")
        return

    user_clients_group_name = get_client_group_name(owner_id)
    await channel_layer.group_send(
        user_clients_group_name,
        {
            "type": "service_removed",
            "event": event.model_dump(mode="json"),
        },
    )


async def broadcast_service_status_update(
    owner_id: int, event: ClientServiceStatusUpdateEvent
) -> None:
    """
    Broadcast service status update event to clients.
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.debug(
            "Channel layer not configured. Cannot broadcast service status update."
        )
        return

    user_clients_group_name = get_client_group_name(owner_id)
    await channel_layer.group_send(
        user_clients_group_name,
        {
            "type": "service_status_update",
            "event": event.model_dump(mode="json"),
        },
    )
