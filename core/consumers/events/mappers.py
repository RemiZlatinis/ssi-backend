from core.consumers.events.typing import (
    ClientAgentDataModel,
    ClientServiceDataModel,
    ServiceStatus,
)
from core.models import Agent


def map_agent_to_client_model(agent: Agent) -> ClientAgentDataModel:
    """Sync helper to map an Agent ORM object to ClientAgentDataModel."""
    agent_services = []
    for svc in agent.services.all():
        agent_services.append(
            ClientServiceDataModel(
                id=svc.agent_service_id,
                name=svc.name,
                description=svc.description or "",
                version=svc.version or "",
                schedule=svc.schedule or "",
                last_message=svc.last_message or "",
                last_seen=svc.last_seen,
                last_status=svc.last_status or ServiceStatus.UNKNOWN,
            )
        )

    return ClientAgentDataModel(
        id=str(agent.pk),
        name=agent.name,
        registration_status=agent.registration_status,
        ip_address=agent.ip_address,
        is_online=agent.is_online,
        last_seen=agent.last_seen,
        services=agent_services,
    )
