from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Agent

User = get_user_model()


class AgentOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class AgentSerializer(serializers.ModelSerializer):
    owner = AgentOwnerSerializer(read_only=True)

    class Meta:
        model = Agent
        fields = [
            "id",
            "name",
            # "key",
            "created_at",
            "owner",
            "ip_address",
            "registration_status",
        ]
        read_only_fields = [
            # "key",
            "created_at",
            "owner",
            "ip_address",
            "registration_status",
        ]


class AgentRegisterSerializer(serializers.Serializer):
    key = serializers.UUIDField()
