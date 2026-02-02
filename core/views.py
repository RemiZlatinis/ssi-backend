import logging
import uuid
from typing import Any, cast

from django.contrib.auth.models import User as AuthUser
from django.db.models.query import QuerySet
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from core.authentication import AgentAuthentication
from core.models import Agent, AgentRegistration
from core.serializers import (
    AgentRegistrationSerializer,
    AgentSerializer,
    CompleteAgentRegistrationSerializer,
)

logger = logging.getLogger("core")


class AgentViewSet(viewsets.ModelViewSet):
    """
    Unified viewset for all agent operations.

    Uses different authentication per action:
    - X-Session-Token (from allauth): list, retrieve, update, destroy (user operations)
    - Agent Key: me, register_finalize (agent operations)
    - None: registration flow endpoints (initiate, status, complete)
    """

    serializer_class = AgentSerializer
    queryset = Agent.objects.none()
    permission_classes = [IsAuthenticated]

    def get_authenticators(self):
        """Override auth for agent-specific actions based on URL path."""
        # Check the URL path to determine which action is being called
        path = self.request.path if hasattr(self, "request") else ""

        # Agent-specific endpoints use Agent Key authentication
        if "/me/" in path or "/finalize/" in path:
            return [AgentAuthentication()]

        return super().get_authenticators()

    def get_permissions(self):
        """Allow any for registration flow endpoints based on URL path."""
        path = self.request.path if hasattr(self, "request") else ""

        # Registration flow endpoints don't require authentication
        if any(
            endpoint in path
            for endpoint in ["/initiate/", "/status/", "/complete/", "/finalize/"]
        ):
            return [AllowAny()]
        return super().get_permissions()

    # =================================================================================#
    # STANDARD ACTIONS (User-facing, Default authentication)                           #
    # =================================================================================#

    def get_queryset(self) -> QuerySet[Agent]:
        """Return only the user's agents."""
        user = self.request.user
        if user.is_authenticated:
            return Agent.objects.filter(owner=user).prefetch_related("services")
        return Agent.objects.none()

    def perform_create(self, serializer):
        """Disable manual agent creation."""
        raise PermissionDenied(
            "Agents cannot be created manually. Use the registration flow."
        )

    # =================================================================================#
    # AGENT SELF-SERVICE (Agent Key authentication)                                    #
    # =================================================================================#

    @action(detail=False, methods=["get", "delete"], url_path="me")
    def me(self, request: Request) -> Response:
        """
        Agent self-service endpoint.

        GET: Returns agent's own data
        DELETE: Agent self-deletion
        """
        agent: Agent = request.auth  # From AgentAuthentication

        if request.method == "DELETE":
            agent.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = AgentSerializer(agent)
        return Response(serializer.data)

    # =================================================================================#
    # REGISTRATION FLOW (Mixed authentication)                                         #
    # =================================================================================#

    @action(detail=False, methods=["post"], url_path="register/initiate")
    @method_decorator(ratelimit(key="ip", rate="5/15m", block=True), name="dispatch")
    def register_initiate(self, request: Request) -> Response:
        """
        Start agent registration process.

        Creates AgentRegistration record with 6-digit code.
        No authentication required.
        """
        registration = AgentRegistration.objects.create()
        serializer = AgentRegistrationSerializer(registration)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="register/complete")
    @method_decorator(ratelimit(key="ip", rate="5/15m", block=True), name="dispatch")
    def register_complete(self, request: Request) -> Response:
        """
        Complete registration via mobile app/dashboard.

        User enters the 6-digit code to claim the agent.
        Requires X-Session-Token authentication.
        """
        serializer = CompleteAgentRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        if not isinstance(validated_data, dict):
            return Response(
                {"detail": "Invalid data format."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        code = validated_data["code"]

        try:
            registration = AgentRegistration.objects.get(
                code=code, status="pending", expires_at__gt=timezone.now()
            )
        except AgentRegistration.DoesNotExist:
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

        # Create agent (PENDING status)
        agent = Agent(
            owner=cast(AuthUser, request.user),
            registration_status=Agent.RegistrationStatus.PENDING,
        )
        agent.name = f"Agent-{str(agent.key)[:8]}"
        agent.save()

        # Store credentials for CLI to retrieve
        registration.status = "completed"
        registration.agent_credentials = cast(Any, {"key": str(agent.key)})
        registration.save()

        return Response(
            {"message": "Agent registered successfully!"},
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["get"],
        url_path=r"register/status/(?P<registration_id>[^/.]+)",
    )
    @method_decorator(ratelimit(key="ip", rate="120/15m", block=True), name="dispatch")
    def register_status(
        self, request: Request, registration_id: str | None = None
    ) -> Response:
        """
        Poll for registration status.

        CLI calls this repeatedly until completed.
        No authentication required.
        """
        try:
            registration_id_uuid = uuid.UUID(registration_id)
            registration = AgentRegistration.objects.get(id=registration_id_uuid)
        except (ValueError, AgentRegistration.DoesNotExist):
            return Response(status=status.HTTP_404_NOT_FOUND)

        if registration.status == "completed":
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

    @action(detail=False, methods=["post"], url_path="register/finalize")
    def register_finalize(self, request: Request) -> Response:
        """
        Finalize agent registration (set to REGISTERED).

        CLI calls this after retrieving key from polling.
        Requires Agent Key in Authorization header.
        """
        agent: Agent = request.auth  # From AgentAuthentication

        if agent.registration_status != Agent.RegistrationStatus.PENDING:
            return Response(
                {"detail": f"Agent is already {agent.registration_status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        agent.registration_status = Agent.RegistrationStatus.REGISTERED
        agent.save()

        return Response(
            {
                "id": agent.pk,
                "name": agent.name,
                "message": f"Agent '{agent.name}' registered successfully!",
            },
            status=status.HTTP_200_OK,
        )
