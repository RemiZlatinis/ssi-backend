from typing import Any

from django.contrib import admin
from django.http import HttpRequest

from .models import Agent, Service


class ServiceInline(admin.TabularInline):
    """
    Displays services as an inline table on the Agent admin page.
    This provides a read-only view, as services are managed by the agent itself.
    """

    model = Service
    extra = 0  # Don't show extra empty forms for adding
    fields = ("name", "agent_service_id", "last_status", "last_seen", "version")
    readonly_fields = fields  # All fields are read-only
    can_delete = False  # Services are managed by the agent

    def has_add_permission(self, request: HttpRequest, obj: Any | None = None) -> bool:
        # Prevent adding new services from the admin
        return False


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "owner",
        "registration_status",
        "is_online",
        "ip_address",
        "created_at",
    )
    list_filter = ("registration_status", "is_online")
    readonly_fields = ("key", "created_at", "ip_address")
    search_fields = ("name", "owner__username")
    inlines = [ServiceInline]


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    """
    Admin view for the Service model. Provides a global, read-only list of all
    services across all agents.
    """

    list_display = ("name", "agent", "last_status", "last_seen", "version")
    list_filter = ("last_status", "agent__name")
    search_fields = ("name", "agent__name")
    # All fields are managed by the agent, so they should be read-only.
    readonly_fields = [field.name for field in Service._meta.fields]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: Any | None = None
    ) -> bool:
        return False
