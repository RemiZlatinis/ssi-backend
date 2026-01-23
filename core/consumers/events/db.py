import logging
import uuid

from channels.db import database_sync_to_async
from django.contrib.auth.models import User

from core.models import Agent, Service

from .mappers import map_agent_to_client_model
from .typing import (
    AgentServiceDataModel,
    AgentServiceStatusUpdatePayload,
)

logger = logging.getLogger(__name__)


@database_sync_to_async
def get_agent(key: uuid.UUID) -> Agent | None:
    """
    Returns the agent with the given key if it exists and is registered, otherwise None.
    """
    try:
        return (
            Agent.objects.prefetch_related("services")
            .select_related("owner")
            .get(key=key, registration_status=Agent.RegistrationStatus.REGISTERED)
        )
    except Agent.DoesNotExist:
        logger.warning(f"Connection attempt with invalid agent key: {key}")
        return None


@database_sync_to_async
def update_agent_ip(agent: Agent, new_ip: str | None) -> None:
    if new_ip and agent.ip_address != new_ip:
        agent.ip_address = new_ip
        agent.save(update_fields=["ip_address"])
        logger.info(f"Updated IP for agent '{agent.name}' to {new_ip}")


@database_sync_to_async
def sync_agent_services_and_set_online(
    agent: Agent, services: list[AgentServiceDataModel]
) -> None:
    """
    Synchronize the agent's services with the given list of services and mark as online.
    """
    incoming_service_ids = {
        service.id  # Those are the human readable IDs from the agent
        for service in services
    }
    for service_data in services:
        Service.objects.update_or_create(
            agent=agent,
            agent_service_id=service_data.id,
            defaults={
                "name": service_data.name,
                "description": service_data.description,
                "version": service_data.version,
                "schedule": service_data.schedule,
            },
        )
    agent.services.exclude(
        agent_service_id__in=incoming_service_ids  # Filter deleted services
    ).delete()

    agent.mark_connected()


@database_sync_to_async
def add_service(agent: Agent, service_data: AgentServiceDataModel) -> None:
    """Creates a service from the given service data"""
    Service.objects.create(
        agent=agent,
        agent_service_id=service_data.id,
        name=service_data.name,
        description=service_data.description,
        version=service_data.version,
        schedule=service_data.schedule,
    )


@database_sync_to_async
def remove_service(agent: Agent, service_id: str) -> None:
    try:
        service = Service.objects.select_related("agent__owner").get(
            agent=agent, agent_service_id=service_id
        )
        service.delete()
    except Service.DoesNotExist:
        logger.warning(f"Service {service_id} not found for agent {agent.pk}")


@database_sync_to_async
def update_service_status(
    agent: Agent, update_data: AgentServiceStatusUpdatePayload
) -> None:
    try:
        service = Service.objects.select_related("agent__owner").get(
            agent=agent, agent_service_id=update_data.service_id
        )
        service.last_status = update_data.status.value
        service.last_message = update_data.message
        service.last_seen = update_data.timestamp
        service.save(update_fields=["last_status", "last_message", "last_seen"])
    except Service.DoesNotExist:
        logger.warning(
            f"Service {update_data.service_id} not found for agent {agent.pk}"
        )


@database_sync_to_async
def get_user_agents(user: User) -> list:
    """
    Returns all user's registered agents as ClientAgentDataModel list
    """
    agents = Agent.objects.filter(
        owner=user, registration_status=Agent.RegistrationStatus.REGISTERED
    ).prefetch_related("services")

    return [map_agent_to_client_model(agent) for agent in agents]
