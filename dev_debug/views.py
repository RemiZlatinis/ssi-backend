import logging
import os

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from core.models import Agent

logger = logging.getLogger(__name__)

# Check if we're in DEBUG mode
DEBUG_MODE = os.environ.get("DEBUG", "False").lower() in ("true", "1", "yes")


@login_required
@require_http_methods(["GET"])
def agent_list(request):
    """
    Development debugging dashboard - agent list view.
    Shows all agents with live status updates via polling.
    """
    # Only available in DEBUG mode
    if not DEBUG_MODE:
        raise PermissionDenied("Debug interface is only available in DEBUG mode")

    agents = Agent.objects.select_related("owner").prefetch_related("services").all()

    context = {
        "agents": agents,
        "total_agents": agents.count(),
        "online_agents": agents.filter(is_online=True).count(),
        "pending_agents": agents.filter(
            registration_status=Agent.RegistrationStatus.PENDING
        ).count(),
        "registered_agents": agents.filter(
            registration_status=Agent.RegistrationStatus.REGISTERED
        ).count(),
    }

    return render(request, "dev_debug/agent_list.html", context)


@login_required
@require_http_methods(["GET"])
def agent_detail(request, agent_id):
    """
    Development debugging dashboard - agent detail view.
    Shows agent details, services, and live event logs.
    """
    # Only available in DEBUG mode
    if not DEBUG_MODE:
        raise PermissionDenied("Debug interface is only available in DEBUG mode")

    agent = get_object_or_404(
        Agent.objects.select_related("owner").prefetch_related("services"), key=agent_id
    )

    # Check if user owns this agent or is staff
    if not (request.user.is_staff or agent.owner == request.user):
        raise PermissionDenied("You can only debug your own agents")

    context = {
        "agent": agent,
        "services": agent.services.all(),
        "websocket_url": f"/dev-debug/ws/agent/{agent_id}/",
        "api_url": f"/dev-debug/api/agent/{agent_id}/",
    }

    return render(request, "dev_debug/agent_detail.html", context)


@login_required
@require_http_methods(["GET"])
def agent_api_detail(request, agent_id):
    """
    API endpoint for polling agent details and services.
    Returns JSON data for the debugging dashboard.
    """
    # Only available in DEBUG mode
    if not DEBUG_MODE:
        raise PermissionDenied("Debug API is only available in DEBUG mode")

    # agent_id is already a UUID object from URL routing, no need to convert
    agent = get_object_or_404(
        Agent.objects.select_related("owner").prefetch_related("services"), key=agent_id
    )

    # Check if user owns this agent or is staff
    if not (request.user.is_staff or agent.owner == request.user):
        raise PermissionDenied("You can only access your own agents")

    # Serialize agent data
    agent_data = {
        "id": str(agent.key),
        "name": agent.name,
        "owner": agent.owner.username,
        "ip_address": agent.ip_address,
        "registration_status": agent.registration_status,
        "is_online": agent.is_online,
        "last_seen": agent.last_seen.isoformat() if agent.last_seen else None,
        "created_at": agent.created_at.isoformat(),
        "services": [
            {
                "id": service.id,
                "agent_service_id": service.agent_service_id,
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
            for service in agent.services.all()
        ],
    }

    return JsonResponse(agent_data)


@login_required
@require_http_methods(["GET"])
def agent_list_api(request):
    """
    API endpoint for polling all agents.
    Returns JSON data for the debugging dashboard list view.
    """
    # Only available in DEBUG mode
    if not DEBUG_MODE:
        raise PermissionDenied("Debug API is only available in DEBUG mode")

    agents = Agent.objects.select_related("owner").prefetch_related("services").all()

    # Filter for current user unless they're staff
    if not request.user.is_staff:
        agents = agents.filter(owner=request.user)

    # Serialize agents data
    agents_data = []
    for agent in agents:
        agent_data = {
            "id": str(agent.key),
            "name": agent.name,
            "owner": agent.owner.username,
            "ip_address": agent.ip_address,
            "registration_status": agent.registration_status,
            "is_online": agent.is_online,
            "last_seen": agent.last_seen.isoformat() if agent.last_seen else None,
            "created_at": agent.created_at.isoformat(),
            "services": [
                {
                    "id": service.id,
                    "name": service.name,
                    "last_status": service.last_status,
                }
                for service in agent.services.all()
            ],
        }
        agents_data.append(agent_data)

    return JsonResponse({"agents": agents_data})
