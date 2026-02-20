import logging
from typing import Any

import httpx
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()

logger = logging.getLogger("notifications")


class Device(models.Model):
    OS_ANDROID = "Android"
    OS_IOS = "iOS"
    OS_UNKNOWN = "Unknown"

    OS_CHOICES = (
        (OS_ANDROID, "Android"),
        (OS_IOS, "iOS"),
        (OS_UNKNOWN, "Unknown"),
    )

    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"

    STATUS_CHOICES = (
        (STATUS_ACTIVE, "🟢 Active"),
        (STATUS_INACTIVE, "🔴 Inactive"),
    )

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notification_devices"
    )
    token = models.CharField(max_length=255, db_index=True)

    manufacturer = models.CharField(max_length=255)
    model_name = models.CharField(max_length=255)
    device_name = models.CharField(max_length=255)
    os_name = models.CharField(max_length=50, choices=OS_CHOICES, default=OS_UNKNOWN)
    os_version = models.CharField(max_length=50, blank=True)

    status = models.CharField(
        max_length=50, choices=STATUS_CHOICES, default=STATUS_ACTIVE
    )

    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "token")

    def __str__(self) -> str:
        return str(self.token)

    async def send_notification(
        self,
        title: str = "Title",
        body: str = "",
        data: dict[str, Any] | None = None,
        channel_id: str | None = None,
        **extra: Any,
    ) -> dict[str, Any] | None:
        if self.status == self.STATUS_INACTIVE:
            return None

        if data is None:
            data = {}

        # Construct the payload
        payload = {
            "to": self.token,
            "title": title,
            "body": body,
            "data": data,
            "channelId": channel_id,
            **extra,
        }

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
                logger.info(f"Notification sent to device {self.pk}: {result}")
                return result
        except httpx.RequestError as e:
            logger.error(f"Error sending notification to device {self.pk}: {e}")
            return None
