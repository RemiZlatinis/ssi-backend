from typing import Any

from asgiref.sync import sync_to_async
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from core.consumers.events.broadcasting import (
    broadcast_agent_status_update,
    broadcast_service_added,
    broadcast_service_removed,
    broadcast_service_status_update,
)
from core.consumers.events.mappers import map_agent_to_client_model
from core.consumers.events.typing import (
    ClientServiceAddedEvent,
    ClientServiceAddedPayload,
    ClientServiceDataModel,
    ClientServiceRemovedEvent,
    ClientServiceRemovedPayload,
    ClientServiceStatusUpdateEvent,
    ClientServiceStatusUpdatePayload,
    ClientStatusUpdateEvent,
    ClientStatusUpdatePayload,
    ServiceStatus,
)
from core.models import Agent, Service
from core.utils import get_static_icon_url
from notifications.models import Device

from .signals import agent_status_changed


@receiver(agent_status_changed)
async def receive_agent_status_changed(sender, instance: Agent, is_online, **kwargs):
    """
    Listens for status changes

    Dispatches notifications to owner devices,
    and broadcasts the change to the user's clients channel group
    """
    if is_online:
        title = f'"{instance.name}" is online'
        icon = "ok.png"
    else:
        title = f'"{instance.name}" went offline'
        icon = "server.png"

    # Fetch devices asynchronously
    owner_devices = await sync_to_async(
        lambda: list(
            Device.objects.filter(user=instance.owner, status=Device.STATUS_ACTIVE)
        )
    )()

    # Send notifications to all devices concurrently
    for device in owner_devices:
        await device.send_notification(
            title=title,
            channel_id="agent-status",
            large_icon=get_static_icon_url(icon),
        )


@receiver(post_save, sender=Agent)
async def post_save_agent(
    sender: type[Agent],
    instance: Agent,
    created: bool,
    update_fields: set[str] | None,
    **kwargs: Any,
) -> None:
    """
    Handles Agent updates and broadcast the changes to all connected clients.
    """
    # Prepare event payload
    agent_model = map_agent_to_client_model(instance)
    client_event = ClientStatusUpdateEvent(
        data=ClientStatusUpdatePayload(agent=agent_model)
    )

    # Broadcast the event
    await broadcast_agent_status_update(instance.owner_id, client_event)


@receiver(pre_save, sender=Service)
async def pre_save_service_status(
    sender: type[Service], instance: Service, **kwargs: Any
) -> None:
    """
    Stores the original 'last_status' of a Service instance before it's saved.
    This allows the post_save signal to compare old and new values.
    """
    if not instance._state.adding:
        try:
            original_service = await sync_to_async(
                lambda: Service.objects.only("last_status").get(pk=instance.pk)
            )()
            instance.__setattr__("_original_last_status", original_service.last_status)
        except Service.DoesNotExist:
            # This can happen in a race condition. Set original status to None
            # so the post_save check will treat it as a change.
            instance.__setattr__("_original_last_status", None)


@receiver(post_save, sender=Service)
async def post_save_service_status(
    sender: type[Service],
    instance: Service,
    created: bool,
    update_fields: set[str] | None,
    **kwargs: Any,
) -> None:
    """
    Handles 'Service' changes.
    - On creation, broadcasts 'service_added'.
    - On 'last_status' update, sends notifications and
      broadcasts 'service_status_update'.
    """

    if created:
        client_service = ClientServiceDataModel(
            id=instance.agent_service_id,
            name=instance.name,
            description=instance.description or "",
            version=instance.version or "",
            schedule=instance.schedule or "",
            last_message=instance.last_message or "",
            last_seen=instance.last_seen,
            last_status=instance.last_status or ServiceStatus.UNKNOWN,
        )
        event = ClientServiceAddedEvent(
            data=ClientServiceAddedPayload(
                agent_id=str(instance.agent.pk), service=client_service
            )
        )
        await broadcast_service_added(instance.agent.owner_id, event)
        return

    # Logic for status updates on existing services
    if update_fields and "last_status" in update_fields:
        # Broadcast the service status update event
        status_event = ClientServiceStatusUpdateEvent(
            data=ClientServiceStatusUpdatePayload(
                agent_id=str(instance.agent_id),
                service_id=instance.agent_service_id,
                status=instance.last_status or ServiceStatus.UNKNOWN,
                message=instance.last_message or "",
                timestamp=instance.last_seen,
            )
        )
        await broadcast_service_status_update(instance.agent.owner_id, status_event)

        # If status changed, send mobile notifications
        old_status = getattr(instance, "_original_last_status", None)
        new_status = instance.last_status
        if old_status != new_status:
            status_lower = new_status.lower() if new_status else "unknown"
            if status_lower not in [
                "ok",
                "warning",
                "error",
                "update",
                "failure",
                "unknown",
            ]:
                status_lower = "unknown"

            channel_id = f"service-{status_lower}"
            icon_name = f"{status_lower}.png"
            user_devices = await sync_to_async(
                lambda: list(
                    Device.objects.filter(
                        user=instance.agent.owner, status=Device.STATUS_ACTIVE
                    )
                )
            )()
            for device in user_devices:
                await device.send_notification(
                    title=f"{instance.name} - {new_status}",
                    body=instance.last_message,
                    channel_id=channel_id,
                    large_icon=get_static_icon_url(icon_name),
                )


@receiver(post_delete, sender=Service)
async def handle_service_deleted(
    sender: type[Service], instance: Service, **kwargs: Any
) -> None:
    """
    Handles 'Service' deletion by broadcasting 'service_removed' event.
    """
    # Skip broadcasting if this service is being cascade-deleted with its agent
    if await sync_to_async(Agent.objects.filter(id=instance.agent_id).exists)():
        return

    event = ClientServiceRemovedEvent(
        data=ClientServiceRemovedPayload(
            agent_id=str(instance.agent_id), service_id=instance.agent_service_id
        )
    )
    await broadcast_service_removed(instance.agent.owner_id, event)
