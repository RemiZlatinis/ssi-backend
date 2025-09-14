from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import Agent


class AgentAuthentication(BaseAuthentication):
    """
    Custom authentication class for Agents.

    Clients should authenticate by passing the agent key in the "Authorization"
    HTTP header, prepended with the string "Agent ". For example:

        Authorization: Agent 401f7ac8-b421-446e-a924-ebb915e61236
    """

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Agent "):
            return None

        try:
            # The header is "Agent <key>", so we split and take the second part
            agent_key = auth_header.split(" ")[1]
            agent = Agent.objects.select_related("owner").get(key=agent_key)
        except (IndexError, Agent.DoesNotExist):
            raise AuthenticationFailed("Invalid agent key.")

        # The authenticate method must return a two-tuple of (user, auth)
        # We'll set the agent's owner as the user and the agent instance as auth
        return (agent.owner, agent)
