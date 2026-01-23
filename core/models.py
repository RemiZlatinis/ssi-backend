import secrets
import string
import uuid
from datetime import timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .signals import agent_status_changed

User = get_user_model()


class Agent(models.Model):
    class RegistrationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        REGISTERED = "registered", "Registered"
        UNREGISTERED = "unregistered", "Unregistered"

    name = models.CharField(
        max_length=50,
        help_text=(
            "A friendly name for the agent. Can be auto-generated on registration."
        ),
    )
    key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="agents")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    registration_status = models.CharField(
        max_length=20,
        choices=RegistrationStatus.choices,
        default=RegistrationStatus.PENDING,
    )

    # State tracking
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of when the agent was disconnected.",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def mark_connected(self) -> None:
        """
        Sets the agent.is_online to True,
        the agent.last_seen to None,
        and trigger the agent_status_changed signal
        """
        self.is_online = True
        self.last_seen = None
        self.save(update_fields=["is_online", "last_seen"])
        agent_status_changed.send(sender=self.__class__, instance=self, is_online=True)

    def mark_disconnected(self) -> None:
        """
        Sets the agent.is_online to False,
        the agent.last_seen to timezone.now(),
        and trigger the agent_status_changed signal
        """
        self.is_online = False
        self.last_seen = timezone.now()
        self.save(update_fields=["is_online", "last_seen"])
        agent_status_changed.send(sender=self.__class__, instance=self, is_online=False)


class Service(models.Model):
    """
    Represents a single service monitored by an agent.
    """

    class Status(models.TextChoices):
        OK = "OK", _("OK")
        WARNING = "WARNING", _("Warning")
        ERROR = "ERROR", _("Error")
        UPDATE = "UPDATE", _("Update")
        FAILURE = "FAILURE", _("Failure")
        UNKNOWN = "UNKNOWN", _("Unknown")

    # Static Information
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="services")
    agent_service_id = models.CharField(
        max_length=255,
        help_text="The local, non-unique ID of the service on the agent machine.",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    version = models.CharField(max_length=50, blank=True)
    schedule = models.CharField(max_length=255, blank=True)

    # Dynamic State (Last Known Update)
    last_status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.UNKNOWN
    )
    last_message = models.TextField(null=False, blank=True)
    last_seen = models.DateTimeField(
        null=True, blank=True, help_text="Timestamp of the last status update."
    )

    class Meta:
        # Ensures that for any given agent, the local service ID is unique.
        unique_together = ("agent", "agent_service_id")
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} on {self.agent.name}"


class AgentRegistration(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("expired", "Expired"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=6, unique=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    expires_at = models.DateTimeField(blank=True)
    failed_attempts = models.PositiveIntegerField(default=0)
    agent_credentials = models.JSONField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Registration {self.id} - {self.status}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self._state.adding:  # On creation
            self.expires_at = timezone.now() + timedelta(minutes=1)
            self.code = self.generate_unique_code()
        super().save(*args, **kwargs)

    def generate_unique_code(self) -> str:
        while True:
            code = "".join(secrets.choice(string.digits) for _ in range(6))
            if not AgentRegistration.objects.filter(
                code=code, status="pending"
            ).exists():
                return code
