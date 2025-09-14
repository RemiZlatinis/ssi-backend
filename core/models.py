import uuid

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Agent(models.Model):
    name = models.CharField(
        max_length=50, help_text="Friendly name provided by the user"
    )
    key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="agents")

    def __str__(self):
        return self.name
