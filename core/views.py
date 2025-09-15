import asyncio
import json

from asgiref.sync import sync_to_async  # Import sync_to_async
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from django.http import StreamingHttpResponse
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import AgentAuthentication, get_client_ip
from .models import Agent
from .serializers import AgentRegisterSerializer, AgentSerializer


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
        if validated_data is None or not isinstance(validated_data, dict):
            return Response(
                {"detail": "Invalid data."}, status=status.HTTP_400_BAD_REQUEST
            )

        key = validated_data.get("key")
        if key is None:
            return Response(
                {"detail": "Key is required."}, status=status.HTTP_400_BAD_REQUEST
            )

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
    Marks an authenticated agent as 'unregistered'.
    """

    authentication_classes = [AgentAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        agent = request.auth
        agent.registration_status = Agent.RegistrationStatus.UNREGISTERED
        agent.save()
        return Response(
            {"message": f"Agent '{agent.name}' has been unregistered."},
            status=status.HTTP_200_OK,
        )


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
