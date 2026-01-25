from typing import Any, Tuple

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from .models import Agent


class AgentAuthentication(BaseAuthentication):
    """
    Custom authentication class for Agents.

    Clients should authenticate by passing the agent key in the "Authorization"
    HTTP header, prepended with the string "Agent ". For example:

        Authorization: Agent 401f7ac8-b421-446e-a924-ebb915e61236
    """

    def authenticate(self, request: Request) -> Tuple[Any, Agent] | None:
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Agent "):
            return None

        try:
            agent_key = auth_header.split(" ")[1]
            agent = Agent.objects.select_related("owner").get(
                key=agent_key, registration_status=Agent.RegistrationStatus.REGISTERED
            )
        except (IndexError, Agent.DoesNotExist):
            raise AuthenticationFailed("Invalid or not registered agent key.")

        return (agent.owner, agent)
