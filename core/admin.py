from django.contrib import admin

from .models import Agent


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at")
    readonly_fields = ("key", "created_at")
