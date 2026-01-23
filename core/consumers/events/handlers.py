import logging

from core.consumers.events.db import (
    add_service,
    remove_service,
    sync_agent_services_and_set_online,
    update_service_status,
)
from core.consumers.events.validation import AgentEventType
from core.models import Agent

logger = logging.getLogger(__name__)


async def handle_agent_event(agent: Agent, event: AgentEventType) -> None:
    """Dispatches agent events"""
    if event.type == "agent.ready":
        logger.debug(f"Agent {agent.pk} is ready.")
        await sync_agent_services_and_set_online(agent, event.data.services)

    elif event.type == "agent.service_added":
        logger.debug(f"Agent {agent.pk} added a new service. [{event.data.service.id}]")
        await add_service(agent, event.data.service)

    elif event.type == "agent.service_removed":
        logger.debug(f"Agent {agent.pk} removed a service. [{event.data.service_id}]")
        await remove_service(agent, event.data.service_id)

    elif event.type == "agent.service_status_update":
        logger.debug(
            f"Agent {agent.pk} updated a service status. [{event.data.service_id}]"
        )
        await update_service_status(agent, event.data)

    else:
        logger.warning(f"Unknown event type: {event.type}")
