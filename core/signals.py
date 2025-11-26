from typing import Any

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from core.models import Service
from core.utils import get_static_icon_url
from notifications.models import Device


@receiver(pre_save, sender=Service)
def pre_save_service_status(
    sender: type[Service], instance: Service, **kwargs: Any
) -> None:
    """
    Stores the original 'last_status' of a Service instance before it's saved.
    This allows the post_save signal to compare old and new values.
    """
    if not instance._state.adding:
        try:
            original_service = Service.objects.only("last_status").get(pk=instance.pk)
            instance.__setattr__("_original_last_status", original_service.last_status)
        except Service.DoesNotExist:
            # This can happen in a race condition. Set original status to None
            # so the post_save check will treat it as a change.
            instance.__setattr__("_original_last_status", None)


@receiver(post_save, sender=Service)
def post_save_service_status(
    sender: type[Service],
    instance: Service,
    created: bool,
    update_fields: set[str] | None,
    **kwargs: Any,
) -> None:
    """
    Prints a message when the 'last_status' of a Service changes.
    """
    # Check if the instance was not just created
    # and 'last_status' was among the updated fields
    if not created and update_fields and "last_status" in update_fields:
        old_status = getattr(instance, "_original_last_status", None)
        new_status = instance.last_status
        if old_status != new_status:
            # Determine channel and icon based on status
            status_lower = new_status.lower() if new_status else "unknown"
            # Validate status to ensure we have a mapping
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

            if instance.agent and instance.agent.owner:
                user = instance.agent.owner
                user_devices = Device.objects.filter(
                    user=user, status=Device.STATUS_ACTIVE
                )
                for device in user_devices:
                    device.send_notification(
                        title=f"{instance.name} - {new_status}",
                        body=instance.last_message,
                        channel_id=channel_id,
                        large_icon=get_static_icon_url(icon_name),
                    )
