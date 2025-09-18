import asyncio
import json
from typing import Any, cast

from asgiref.sync import async_to_sync, sync_to_async
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from django.http import StreamingHttpResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
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


class AgentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A read-only ViewSet that provides `list` and `retrieve` actions
    for agents, including their nested services.
    """

    serializer_class = AgentSerializer
    permission_classes = [IsAuthenticated]

    # Do you want a headache? Remove the # type ignore
    def get_queryset(self):  # type: ignore
        """
        This view should return a list of all the agents
        for the currently authenticated user.
        It uses prefetch_related to optimize the query for services.
        """
        user = self.request.user
        if user.is_authenticated:
            return Agent.objects.filter(owner=user).prefetch_related("services")
        return Agent.objects.none()


class AgentRegisterView(APIView):
    """
    Finalizes the registration of an agent by its key.
    This is a public endpoint.
    """

    def post(self, request, *args, **kwargs):
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
            {"message": f"Agent '{agent.name}' registered successfully!"},
            status=status.HTTP_200_OK,
        )


class AgentUnregisterView(APIView):
    """
    Marks an authenticated agent as 'unregistered' and deletes its services.
    """

    authentication_classes = [AgentAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        agent = request.auth

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
    def post(self, request, *args, **kwargs):
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

    def post(self, request, *args, **kwargs):
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
        name = validated_data["name"]

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
        agent = Agent.objects.create(
            owner=request.user,
            name=name,
            registration_status=Agent.RegistrationStatus.REGISTERED,
        )

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
    def get(self, request, registration_id, *args, **kwargs):
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

    def get(self, request, *args, **kwargs):
        """
        Returns information about the agent making the request.
        """
        agent = request.auth
        serializer = AgentSerializer(agent)
        return Response(serializer.data)


async def sse_agent_status(request):
    """
    A view that streams agent connection status and service updates
    using Server-Sent Events.
    """
    # Resolve request.user and its properties in an async-safe way
    # request.user is a SimpleLazyObject that performs synchronous operations
    # when its properties (like is_authenticated or id) are accessed.
    # We need to ensure this resolution happens in a thread.
    user = await sync_to_async(lambda: request.user)()
    is_authenticated = await sync_to_async(lambda: user.is_authenticated)()

    if not is_authenticated:
        return StreamingHttpResponse(
            [
                (
                    f"data: {json.dumps({'error': 'Authentication required'})}\n\n"
                ).encode("utf-8")
            ],
            content_type="text/event-stream",
            status=401,
        )

    # Dynamically define a group name based on the authenticated user's ID
    user_id = await sync_to_async(lambda: user.id)()
    USER_AGENT_STATUS_GROUP_NAME = f"user_{user_id}_agent_status_updates"

    async def event_stream():
        channel_layer = get_channel_layer()
        if not channel_layer:
            # If channel layer is not configured (e.g., in-memory without run_asgi),
            # we can't stream real-time updates.
            yield (
                f"data: {json.dumps({'error': 'Channel layer not configured'})}\n\n"
            ).encode("utf-8")
            return

        # Create a unique channel for this client to listen on
        channel_name = await channel_layer.new_channel()
        await channel_layer.group_add(USER_AGENT_STATUS_GROUP_NAME, channel_name)

        try:
            # Send the initial list of all agents and their current status
            # get_all_agent_statuses is already @database_sync_to_async,
            # so passing `user` is fine.
            initial_statuses = await get_all_agent_statuses(user)
            yield (
                f"data: {json.dumps({'type': 'initial_status',
                                     'agents': initial_statuses})}"
                f"\n\n"
            ).encode("utf-8")

            # Listen for messages from the group
            while True:
                message = await channel_layer.receive(channel_name)
                if message["type"] == "agent.status.update":
                    data = {
                        "type": "agent_status_update",
                        "agent_id": message["agent_id"],
                        "agent_name": message["agent_name"],
                        "is_online": message["is_online"],
                        "ip_address": message.get("ip_address", None),
                    }
                    yield f"data: {json.dumps(data)}\n\n".encode("utf-8")
                elif message["type"] == "service.status.update":
                    data = {
                        "type": "service_status_update",
                        "agent_id": message["agent_id"],
                        "agent_name": message["agent_name"],
                        "service_id": message["service_id"],
                        "status": message["status"],
                        "message": message["message"],
                        "timestamp": message["timestamp"],
                    }
                    yield f"data: {json.dumps(data)}\n\n".encode("utf-8")
                elif message["type"] == "service.removed":
                    data = {
                        "type": "service_removed",
                        "agent_id": message["agent_id"],
                        "agent_name": message["agent_name"],
                        "service_id": message["service_id"],
                    }
                    yield f"data: {json.dumps(data)}\n\n".encode("utf-8")
                elif message["type"] == "service.added":
                    data = {
                        "type": "service_added",
                        "agent_id": message["agent_id"],
                        "agent_name": message["agent_name"],
                        "service_id": message["service_id"],
                        "name": message["name"],
                        "description": message["description"],
                        "version": message["version"],
                        "schedule": message["schedule"],
                        "last_status": message["last_status"],
                        "last_message": message["last_message"],
                        "last_seen": message["last_seen"],
                    }
                    yield f"data: {json.dumps(data)}\n\n".encode("utf-8")
                # A small sleep to prevent a tight loop if the connection breaks
                await asyncio.sleep(0.1)
        finally:
            # Clean up when the client disconnects
            if channel_layer:
                await channel_layer.group_discard(
                    USER_AGENT_STATUS_GROUP_NAME, channel_name
                )

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    return response


@database_sync_to_async
def get_all_agent_statuses(user):
    """
    Fetches all registered agents for a given user and their current online status
    from the database. Also fetches their services and their last known status.
    """
    agents = Agent.objects.filter(
        owner=user, registration_status=Agent.RegistrationStatus.REGISTERED
    ).prefetch_related("services")

    all_data = []
    for agent in agents:
        agent_data = {
            "agent_id": str(agent.pk),
            "agent_name": agent.name,
            "is_online": agent.is_online,  # Use the is_online field
            "ip_address": agent.ip_address,
            "registration_status": agent.registration_status,
            "services": [],
        }
        for service in agent.services.all():  # type: ignore
            agent_data["services"].append(
                {
                    "service_id": service.agent_service_id,
                    "name": service.name,
                    "description": service.description,
                    "version": service.version,
                    "schedule": service.schedule,
                    "last_status": service.last_status,
                    "last_message": service.last_message,
                    "last_seen": (
                        service.last_seen.isoformat() if service.last_seen else None
                    ),
                }
            )
        all_data.append(agent_data)
    return all_data
