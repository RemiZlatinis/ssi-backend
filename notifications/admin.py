from typing import Any

from django.contrib import admin, messages
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html

from .models import Device


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "token",
        "device_name",
        "os_name",
        "status",
        "send_test_notification_button",
    ]
    list_filter = ["user", "status"]
    search_fields = ["user__username", "user__email", "token", "device_name"]

    readonly_fields = [
        "user",
        "token",
        "manufacturer",
        "model_name",
        "os_name",
        "os_version",
        "added_at",
        "updated_at",
        "send_test_notification_button",
    ]

    def get_urls(self) -> list[Any]:
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/test-notification/",
                self.admin_site.admin_view(self.process_test_notification),
                name="notifications_device_test_notification",
            )
        ]
        return custom_urls + urls

    def send_test_notification_button(self, obj: Device) -> str:
        if obj.pk:
            url = reverse("admin:notifications_device_test_notification", args=[obj.pk])
            return format_html(
                '<a class="button" href="{}">Send Test Notification</a>', url
            )
        return ""

    send_test_notification_button.short_description = "Actions"  # type: ignore

    def process_test_notification(
        self, request: HttpRequest, object_id: str, *args: Any, **kwargs: Any
    ) -> HttpResponseRedirect:
        device = self.get_object(request, object_id)
        if device:
            result = device.send_notification(
                title="Push Notification Test",
                body="If you are seeing this, that means the push notifications"
                " are working correctly with this device",
            )
            if result:
                receipts = result.get("data", [])
                if receipts and isinstance(receipts, list) and len(receipts) > 0:
                    receipt = receipts[0]
                    status = receipt.get("status")
                    if status == "ok":
                        self.message_user(
                            request,
                            "Test notification sent successfully.",
                            messages.SUCCESS,
                        )
                    else:
                        error_message = receipt.get("message", "Unknown error.")
                        self.message_user(
                            request,
                            f"Failed to send test notification: {error_message}",
                            messages.ERROR,
                        )
                else:
                    self.message_user(
                        request,
                        "No receipt data received from push service.",
                        messages.ERROR,
                    )
            else:
                self.message_user(
                    request,
                    "Failed to send test notification. Check server logs.",
                    messages.ERROR,
                )

        return HttpResponseRedirect(
            reverse("admin:notifications_device_change", args=[object_id])
        )
