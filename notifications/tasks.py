"""
Django 6.0 Tasks for Notifications.

Tasks execute synchronously via ImmediateBackend.
Called with .enqueue() for Django 6.0 API compatibility and future async upgrade.
"""

import logging
from typing import Any

import httpx
from django.tasks import task


@task
async def send_push_notification(
    device_token: str,
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
    channel_id: str | None = None,
    large_icon: str | None = None,
) -> dict[str, Any] | None:
    """
    Send a push notification to a device.

    Usage:
        send_push_notification.enqueue(
            device_token="ExponentPushToken[xxx]",
            title="Agent Offline",
            body="Your agent 'Server-01' is offline",
        )

    Args:
        device_token: The push notification token from the device
        title: Notification title
        body: Notification body
        data: Optional data payload
        channel_id: Optional Android channel ID
        large_icon: Optional large icon URL for Android

    Returns:
        The response from the Expo push service, or None on failure
    """

    logger = logging.getLogger("notifications.tasks")

    if data is None:
        data = {}

    # Construct the payload
    payload = {
        "to": device_token,
        "title": title,
        "body": body,
        "data": data,
    }

    # Add Android-specific fields
    if channel_id or large_icon:
        android_payload = payload.get("android", {})
        if channel_id:
            android_payload["channelId"] = channel_id
        if large_icon:
            android_payload["largeIcon"] = large_icon
        payload["android"] = android_payload

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://exp.host/--/api/v2/push/send",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Accept-Encoding": "gzip",
                },
                json=[payload],
            )
            result: dict[str, Any] = response.json()
            logger.info(f"Push notification sent to device: {result}")
            return result
    except httpx.RequestError as e:
        logger.error(f"Error sending push notification: {e}")
        return None


@task
async def send_bulk_notifications(
    device_tokens: list[str],
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
) -> list[dict[str, Any] | None]:
    """
    Send push notifications to multiple devices.

    Usage:
        send_bulk_notifications.enqueue(
            device_tokens=["token1", "token2"],
            title="Alert",
            body="Maintenance scheduled",
        )

    Args:
        device_tokens: List of device push notification tokens
        title: Notification title
        body: Notification body
        data: Optional data payload for all notifications

    Returns:
        List of responses from the Expo push service
    """
    results = []
    for token in device_tokens:
        result = await send_push_notification(
            device_token=token,
            title=title,
            body=body,
            data=data,
        )
        results.append(result)
    return results


@task
def notify_agent_status_change(
    user_id: int,
    agent_name: str,
    is_online: bool,
) -> None:
    """
    Notify all user's devices when an agent's status changes.

    Usage (in signal handler or view):
        notify_agent_status_change.enqueue(
            user_id=agent.owner_id,
            agent_name=agent.name,
            is_online=False,
        )

    Args:
        user_id: The ID of the user to notify
        agent_name: Name of the agent that changed status
        is_online: New online status of the agent
    """
    import logging

    logger = logging.getLogger("notifications.tasks")

    # Import here to avoid circular imports
    from notifications.models import Device

    status_text = "online" if is_online else "offline"
    title = f"Agent {status_text.title()}"
    body = f"Your agent '{agent_name}' is now {status_text}"

    # Get all active devices for the user
    devices = Device.objects.filter(
        user_id=user_id,
        status=Device.STATUS_ACTIVE,
    )

    sent_count = 0
    for device in devices:
        try:
            device.send_notification(
                title=title,
                body=body,
                data={
                    "agent_name": agent_name,
                    "is_online": is_online,
                    "type": "agent_status_change",
                },
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Failed to send notification to device {device.id}: {e}")

    logger.info(
        f"Sent {sent_count} notifications to user {user_id} for agent {agent_name}"
    )
