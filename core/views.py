import logging
import uuid
from typing import Any, cast

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.models import User as AuthUser
from django.db.models.query import QuerySet
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.views import APIView

from .authentication import AgentAuthentication
from .models import Agent, AgentRegistration
from .serializers import (
    AgentRegisterSerializer,
    AgentRegistrationSerializer,
    AgentSerializer,
    CompleteAgentRegistrationSerializer,
)
from .utils import get_client_ip

logger = logging.getLogger("core")


class AgentViewSet(mixins.UpdateModelMixin, viewsets.ReadOnlyModelViewSet):
    """
    A ViewSet that provides `list`, `retrieve`, and `partial_update` actions
    for agents.

    This allows users to view their agents and rename them (via PATCH).
    """

    serializer_class = AgentSerializer
    permission_classes = [IsAuthenticated]

    # Do you want a headache? Remove the # type ignore
    def get_queryset(self) -> QuerySet[Agent]:
        """
        This view should return a list of all the agents
        for the currently authenticated user.
        It uses prefetch_related to optimize the query for services.
        """
        user = self.request.user
        if user.is_authenticated:
            return Agent.objects.filter(owner=user).prefetch_related("services")
        return Agent.objects.none()

    def perform_update(self, serializer: BaseSerializer[Any]) -> None:
        """
        Override to broadcast a real-time event after updating the agent.
        """
        # First, save the instance to apply the update
        super().perform_update(serializer)

        # After saving, get the updated instance and its owner
        agent = serializer.instance
        if agent:
            owner = agent.owner

            # Get the channel layer to send a notification
            channel_layer = get_channel_layer()
            if channel_layer:
                # Define the group name for the agent's owner
                group_name = f"user_{owner.id}_agent_status_updates"

                # Send a message to the group with the updated agent data.
                # We reuse the 'agent.status.update' event to simplify client-side
                # logic, as it can handle both status and data changes like renaming.
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    {
                        "type": "agent.status.update",
                        "agent_id": str(agent.pk),
                        "agent_name": agent.name,  # The new name
                        "is_online": agent.is_online,
                        "ip_address": agent.ip_address,
                        "last_seen": (
                            agent.last_seen.isoformat() if agent.last_seen else None
                        ),
                    },
                )


class AgentRegisterView(APIView):
    """
    Finalizes the registration of an agent by its key.
    This is a public endpoint.
    """

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = AgentRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        if not isinstance(validated_data, dict):
            return Response(
                {"detail": "Invalid data."}, status=status.HTTP_400_BAD_REQUEST
            )

        key = validated_data["key"]
        try:
            agent = Agent.objects.get(key=key)
        except Agent.DoesNotExist:
            return Response(
                {"detail": "Invalid registration key."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if agent.registration_status != Agent.RegistrationStatus.PENDING:
            return Response(
                {"detail": f"Agent is already {agent.registration_status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        agent.registration_status = Agent.RegistrationStatus.REGISTERED
        agent.ip_address = get_client_ip(request)
        agent.save()

        return Response(
            {
                "id": agent.pk,
                "name": agent.name,
                "message": f"Agent '{agent.name}' registered successfully!",
            },
            status=status.HTTP_200_OK,
        )


class AgentUnregisterView(APIView):
    """
    Marks an authenticated agent as 'unregistered' and deletes its services.
    """

    authentication_classes = [AgentAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        agent = cast(Agent, request.auth)

        # First, delete all associated services for a clean slate.
        # This prevents orphaned service records.
        agent.services.all().delete()

        agent.registration_status = Agent.RegistrationStatus.UNREGISTERED
        agent.save(update_fields=["registration_status"])

        # Get the channel layer and send a message to force disconnection
        channel_layer = get_channel_layer()
        if channel_layer:
            agent_group_name = f"agent_{agent.key}"
            async_to_sync(channel_layer.group_send)(
                agent_group_name,
                {
                    "type": "force.disconnect",
                },
            )

        return Response(
            {
                "message": f"Agent '{agent.name}' has been unregistered"
                " and its services removed."
            },
            status=status.HTTP_200_OK,
        )


class InitiateAgentRegistrationView(APIView):
    """
    Starts the agent registration process by generating a 6-digit code.
    """

    @method_decorator(ratelimit(key="ip", rate="5/15m", block=True), name="post")
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        registration = AgentRegistration.objects.create()
        serializer = AgentRegistrationSerializer(registration)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@method_decorator(ratelimit(key="ip", rate="5/15m", block=True), name="post")
class CompleteAgentRegistrationView(APIView):
    """
    Completes the agent registration using a 6-digit code.
    This endpoint is rate-limited to prevent brute-force attacks.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = CompleteAgentRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        if not isinstance(validated_data, dict):
            # This case should not be reached if validation is successful,
            # but it acts as a type guard for static analysis.
            return Response(
                {"detail": "Invalid data format."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        code = validated_data["code"]

        try:
            registration = AgentRegistration.objects.get(
                code=code,
                status="pending",
                expires_at__gt=timezone.now(),
            )
        except AgentRegistration.DoesNotExist:
            # Generic error to avoid leaking information
            return Response(
                {"detail": "Invalid or expired code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if registration.failed_attempts >= 5:
            registration.status = "expired"
            registration.save()
            return Response(
                {"detail": "Too many failed attempts. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create the agent for the user who initiated the registration
        # A temporary name is generated. The user can rename it later.
        agent = Agent(
            owner=cast(AuthUser, request.user),
            registration_status=Agent.RegistrationStatus.REGISTERED,
        )
        agent.name = f"Agent-{str(agent.key)[:8]}"
        agent.save()

        # Store credentials and mark as completed
        registration.status = "completed"
        registration.agent_credentials = cast(Any, {"key": str(agent.key)})
        registration.save()

        return Response(
            {"message": "Agent registered successfully!"}, status=status.HTTP_200_OK
        )


class AgentRegistrationStatusView(APIView):
    """
    Allows the CLI to poll for the status of a registration attempt.
    """

    # CLI does 12/1m this allows 2 attempts in a row
    @method_decorator(ratelimit(key="ip", rate="120/15m", block=True), name="get")
    def get(
        self, request: Request, registration_id: uuid.UUID, *args: Any, **kwargs: Any
    ) -> Response:
        try:
            registration = AgentRegistration.objects.get(id=registration_id)
        except AgentRegistration.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if registration.status == "completed":
            # Clean up and return credentials
            credentials = registration.agent_credentials
            registration.delete()
            return Response({"status": "completed", "credentials": credentials})
        elif (
            registration.status == "expired" or registration.expires_at < timezone.now()
        ):
            registration.delete()
            return Response({"status": "expired"}, status=status.HTTP_410_GONE)
        else:
            return Response({"status": "pending"})


class AgentMeView(APIView):
    authentication_classes = [AgentAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        Returns information about the agent making the request.
        """
        agent = request.auth
        serializer = AgentSerializer(agent)
        return Response(serializer.data)
