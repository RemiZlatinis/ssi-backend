from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Agent, AgentRegistration, Service

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
    Serializer for the Agent model.
    Allows updating the agent's name, but other fields are read-only.
    """

    # This will nest the serialized services under each agent
    services = ServiceSerializer(many=True, read_only=True)
    owner = AgentOwnerSerializer(read_only=True)

    class Meta:
        model = Agent
        fields = [
            "id",
            "name",
            "owner",
            "ip_address",
            "registration_status",
            "created_at",
            "last_seen",
            "grace_period",
            "services",  # The nested list of services
        ]
        read_only_fields = [
            "id",
            "owner",
            "ip_address",
            "registration_status",
            "created_at",
            "last_seen",
            "services",
        ]


class AgentRegisterSerializer(serializers.Serializer):
    """
    Serializer for validating the agent registration key.
    """

    key = serializers.UUIDField()

    class Meta:
        fields = ["key"]


class AgentRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentRegistration
        fields = ["id", "code", "status", "expires_at"]
        read_only_fields = ["id", "status", "expires_at"]


class CompleteAgentRegistrationSerializer(serializers.Serializer):
    """
    Serializer for completing agent registration with a code.
    """

    code = serializers.CharField(max_length=6, min_length=6)
