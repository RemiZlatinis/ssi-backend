from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Agent, Service

User = get_user_model()


class ServiceSerializer(serializers.ModelSerializer):
    """
    Serializer for the Service model.
    """

    class Meta:
        model = Service
        # We list all fields for a comprehensive view
        fields = [
            "id",
            "agent_service_id",
            "name",
            "description",
            "version",
            "schedule",
            "last_status",
            "last_message",
            "last_seen",
        ]


class AgentOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class AgentSerializer(serializers.ModelSerializer):
    """
    Serializer for the Agent model, with nested services.
    """

    # This will nest the serialized services under each agent
    services = ServiceSerializer(many=True, read_only=True)
    owner = serializers.StringRelatedField()

    class Meta:
        model = Agent
        fields = [
            "id",
            "name",
            "owner",
            "ip_address",
            "registration_status",
            "created_at",
            "services",  # The nested list of services
        ]


class AgentRegisterSerializer(serializers.Serializer):
    """
    Serializer for validating the agent registration key.
    """

    key = serializers.UUIDField()

    class Meta:
        fields = ["key"]
