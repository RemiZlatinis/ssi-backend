from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import AgentAuthentication
from .serializers import AgentSerializer


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
