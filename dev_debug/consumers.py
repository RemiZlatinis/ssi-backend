import json
import logging
from typing import Any

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from core.consumers.groups import get_client_group_name

logger = logging.getLogger(__name__)

# Debug route mapping
print("DEBUG: DebugDashboardConsumer loaded")
logger.info("DebugDashboardConsumer initialized for agent listening")


class DebugDashboardConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for the debugging dashboard.
    Listens to both agent events and client broadcast events for a specific agent.
    """

    agent_debug_group_name: str | None = None
    client_group_name: str | None = None
    agent_key: str | None = None
    session_events: list[dict[str, Any]] = []

    async def connect(self) -> None:
        """Authenticate user and join relevant channel groups."""

        # Get agent ID from URL
        self.agent_key = (
            self.scope.get("url_route", {}).get("kwargs", {}).get("agent_key")
        )
        if not self.agent_key:
            await self.close(code=4004, reason="Agent ID required")
            return

        # Set up group names
        self.agent_debug_group_name = f"agent_debug_{self.agent_key}"

        # Get the agent to find its owner for client group
        try:
            from core.models import Agent

            agent = await database_sync_to_async(Agent.objects.get)(key=self.agent_key)
            self.client_group_name = get_client_group_name(agent.owner_id)
        except Agent.DoesNotExist:
            await self.close(code=4004, reason="Agent not found")
            return

        # Accept the connection
        await self.accept()

        # Join agent debug and client groups to listen to events
        try:
            await self.channel_layer.group_add(
                self.agent_debug_group_name, self.channel_name
            )
            logger.info(
                "Debug consumer joined agent debug group: "
                f"{self.agent_debug_group_name}"
            )
        except Exception as e:
            logger.error(
                f"Failed to join agent debug group {self.agent_debug_group_name}: {e}"
            )

        try:
            await self.channel_layer.group_add(
                self.client_group_name, self.channel_name
            )
            logger.info(f"Debug consumer joined client group: {self.client_group_name}")
        except Exception as e:
            logger.error(f"Failed to join client group {self.client_group_name}: {e}")

        # Send initial connection confirmation
        message = f"Connected to debug dashboard for agent {self.agent_key}"
        await self.send(
            text_data=json.dumps(
                {
                    "type": "connection_established",
                    "agent_key": str(self.agent_key),
                    "message": message,
                }
            )
        )

    async def disconnect(self, code: int) -> None:
        """Leave channel groups when disconnecting."""
        if self.agent_debug_group_name:
            await self.channel_layer.group_discard(
                self.agent_debug_group_name, self.channel_name
            )
        if self.client_group_name:
            await self.channel_layer.group_discard(
                self.client_group_name, self.channel_name
            )

    async def receive(
        self, text_data: str | None = None, bytes_data: bytes | None = None
    ) -> None:
        """Handle incoming messages from agent channel group."""
        if not text_data:
            return

        try:
            # Parse as JSON (agent messages are JSON)
            event_data = json.loads(text_data)

            # Create debug-friendly event structure
            agent_event = {
                "type": "agent_event",
                "event_type": event_data.get("type", "unknown"),
                "data": event_data.get("data", event_data),
                "timestamp": timezone.now().isoformat(),
                "source": "agent",
                "raw_message": text_data,  # Include raw message for debugging
            }

            # Send to dashboard
            await self.send(text_data=json.dumps(agent_event))

        except Exception as e:
            # Handle parsing errors
            error_event = {
                "type": "agent_event",
                "event_type": "error",
                "data": {"error": str(e), "raw": text_data},
                "timestamp": timezone.now().isoformat(),
                "source": "debug_system",
            }
            await self.send(text_data=json.dumps(error_event))

    async def agent_debug_message(self, event: dict[str, Any]) -> None:
        """
        Handler for messages intercepted by AgentMessageSnifferMiddleware.
        """
        text_data = event.get("text")
        if not text_data:
            return

        try:
            # Parse as JSON
            event_data = json.loads(text_data)

            # Create debug-friendly event structure
            agent_event = {
                "type": "agent_event",
                "event_type": event_data.get("type", "unknown"),
                "data": event_data.get("data", event_data),
                "timestamp": timezone.now().isoformat(),
                "source": "agent_sniffer",
                "raw_message": text_data,
            }

            # Send to dashboard
            await self.send(text_data=json.dumps(agent_event))

        except Exception as e:
            logger.error(f"Error forwarding debug message: {e}")

    async def status_update(self, event: dict[str, Any]) -> None:
        """Handler for 'status_update' messages from client group."""
        await self._forward_client_event(event)

    async def service_added(self, event: dict[str, Any]) -> None:
        """Handler for 'service_added' messages from client group."""
        await self._forward_client_event(event)

    async def service_removed(self, event: dict[str, Any]) -> None:
        """Handler for 'service_removed' messages from client group."""
        await self._forward_client_event(event)

    async def service_status_update(self, event: dict[str, Any]) -> None:
        """Handler for 'service_status_update' messages from client group."""
        await self._forward_client_event(event)

    async def _forward_client_event(self, event: dict[str, Any]) -> None:
        """Helper to forward client group events to the dashboard."""
        client_event_data = event.get("event")
        if not client_event_data:
            return

        try:
            # Create debug-friendly event structure
            dashboard_event = {
                "type": "client_event",
                "event_type": client_event_data.get("type", "unknown"),
                "data": client_event_data.get("payload", client_event_data),
                "timestamp": timezone.now().isoformat(),
                "source": "client",
            }

            # Send to dashboard
            await self.send(text_data=json.dumps(dashboard_event))
        except Exception as e:
            logger.error(f"Error forwarding client event: {e}")
