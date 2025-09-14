from django.contrib import admin

from .models import Agent


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "registration_status", "ip_address", "created_at")
    list_filter = ("registration_status",)
    readonly_fields = ("key", "created_at", "ip_address")
    search_fields = ("name", "owner__username")
