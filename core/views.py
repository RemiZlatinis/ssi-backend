from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import AgentAuthentication, get_client_ip
from .models import Agent
from .serializers import AgentRegisterSerializer, AgentSerializer


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
