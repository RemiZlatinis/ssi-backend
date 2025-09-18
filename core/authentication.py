from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import Agent
from .utils import get_client_ip


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
            agent_key = auth_header.split(" ")[1]
            agent = Agent.objects.select_related("owner").get(
                key=agent_key, registration_status=Agent.RegistrationStatus.REGISTERED
            )
        except (IndexError, Agent.DoesNotExist):
            raise AuthenticationFailed("Invalid or not registered agent key.")

        # Update IP address on successful authentication
        current_ip = get_client_ip(request)
        print(agent.ip_address, current_ip)
        if agent.ip_address != current_ip:
            agent.ip_address = current_ip
            agent.save(update_fields=["ip_address"])

        return (agent.owner, agent)
