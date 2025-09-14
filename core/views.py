import asyncio
import json

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
    A view that streams agent connection status updates using Server-Sent Events.
    """

    async def event_stream():
        # Create a unique channel for this client to listen on
        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        channel_name = await channel_layer.new_channel()
        await channel_layer.group_add("agent_status", channel_name)

        try:
            # Send the initial list of all agents and their current status
            initial_statuses = await get_all_agent_statuses()
            yield f"data: {json.dumps(initial_statuses)}\n\n".encode("utf-8")

            # Listen for messages from the group
            while True:
                message = await channel_layer.receive(channel_name)
                if message["type"] == "agent.status.update":
                    data = {
                        "agent_id": message["agent_id"],
                        "agent_name": message["agent_name"],
                        "status": message["status"],
                    }
                    # SSE format: "data: <json_string>\n\n"
                    yield f"data: {json.dumps(data)}\n\n".encode("utf-8")
                # A small sleep to prevent a tight loop if the connection breaks
                await asyncio.sleep(0.1)
        finally:
            # Clean up when the client disconnects
            if channel_layer:
                await channel_layer.group_discard("agent_status", channel_name)

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    return response


@database_sync_to_async
def get_all_agent_statuses():
    """
    Fetches all agents and determines their current connection status.
    NOTE: This is a simplified status check. For a real-world scenario,
    you would have a more robust presence tracking system (e.g., using Redis).
    """
    # This is a simplification. In-memory layer doesn't expose connections.
    # We will assume all agents are disconnected initially and rely on live updates.
    # With Redis, you could query presence more effectively.
    agents = Agent.objects.filter(
        registration_status=Agent.RegistrationStatus.REGISTERED
    )
    statuses = [
        {"agent_id": str(agent.pk), "agent_name": agent.name, "status": "disconnected"}
        for agent in agents
    ]
    return statuses
