import uuid

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Agent(models.Model):
    class RegistrationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        REGISTERED = "registered", "Registered"
        UNREGISTERED = "unregistered", "Unregistered"

    name = models.CharField(
        max_length=50, help_text="Friendly name provided by the user"
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

    def __str__(self):
        return self.name
