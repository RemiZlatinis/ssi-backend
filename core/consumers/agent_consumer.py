import asyncio
import json
import logging
import uuid

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db.utils import DatabaseError
from django.utils import timezone

from core.consumers.events import (
    agent_event_type_adapter,
    get_agent,
    handle_agent_event,
    update_agent_ip,
)
from core.models import Agent
from core.utils import get_client_ip

logger = logging.getLogger(__name__)


class AgentConsumer(AsyncWebsocketConsumer):
    """
    Consumes a WebSocket connection from an agent.
    """

    agent: Agent | None = None

    async def connect(self) -> None:
        # Get the agent key from the URL
        agent_key = self.scope.get("url_route", {}).get("kwargs", {}).get("agent_key")

        # Validate the agent key is a valid UUID
        try:
            agent_key = uuid.UUID(agent_key)
        except ValueError:
            await self.close(code=4001, reason="Invalid agent key")
            return

        # Get the agent from the database
        self.agent = await get_agent(agent_key)

        # Verify the agent exists
        if not self.agent:
            await self.close(
                code=4001,
                reason="Invalid agent key",
            )
            return

        # Ensure only one connection per agent is active at a time
        self.superseded = False
        self.agent_group_name = f"agent_{self.agent.pk}"

        # Broadcast to the group that a new connection is established
        await self.channel_layer.group_send(
            self.agent_group_name,
            {
                "type": "supersede.connection",
                "new_channel_name": self.channel_name,
            },
        )

        # Join the group to receive future supersede events
        await self.channel_layer.group_add(self.agent_group_name, self.channel_name)

        # Accept the connection (We are now receiving messages from the agent)
        await self.accept()

        # Update the agent's IP
        await update_agent_ip(agent=self.agent, new_ip=get_client_ip(self.scope))

    async def receive(
        self,
        text_data: str | None = None,
        bytes_data: bytes | None = None,
    ) -> None:
        if not text_data or not self.agent:
            return

        try:
            # Parsing and validate incoming event payload dynamically
            event = agent_event_type_adapter.validate_json(text_data)

            await handle_agent_event(self.agent, event)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON from agent {self.agent.pk}")
        except Exception as e:
            logger.error(f"Error in AgentConsumer.receive: {e}", exc_info=True)

    async def supersede_connection(self, event: dict) -> None:
        """
        Received when a redundant client connects for the SAME agent.
        We close ourselves forcefully to prevent database state collision.
        """
        if event.get("new_channel_name") != self.channel_name:
            self.superseded = True
            if self.agent:
                logger.info(
                    f"Agent {self.agent.pk} opened a new connection. "
                    "Closing this superseded socket."
                )
            await self.close(code=4000)

    async def disconnect(self, code: int) -> None:
        """Handle agent disconnection with grace period support."""
        # Unsubscribe from group
        if getattr(self, "agent_group_name", None):
            await self.channel_layer.group_discard(
                self.agent_group_name, self.channel_name
            )

        # Do not modify the database if we were kicked by a newer connection
        if getattr(self, "superseded", False):
            logger.debug(
                f"Ignoring disconnect for superseded channel {self.channel_name}"
            )
            return

        try:
            if self.agent:
                # Refresh from DB before checking last_seen
                await database_sync_to_async(self.agent.refresh_from_db)()

                if self.agent.last_seen is None:  # is currently connected
                    self.agent.last_seen = timezone.now()  # mark disconnection time
                    await database_sync_to_async(self.agent.save)(
                        update_fields=["last_seen"]
                    )

                # If grace period is 0, mark disconnected immediately
                if self.agent.grace_period == 0:
                    await database_sync_to_async(self.agent.mark_disconnected)()
                    return

                # Fire-and-forget
                asyncio.create_task(self._grace_period_disconnect(self.agent))
        except DatabaseError:
            logger.error("Database error while disconnecting agent", exc_info=True)

    async def _grace_period_disconnect(self, agent: Agent) -> None:
        """
        Background task to check if agent reconnected within grace period.
        Runs independently, avoiding blocking of the main ASGI handler.
        """
        try:
            await asyncio.sleep(agent.grace_period)
            await database_sync_to_async(agent.refresh_from_db)()
            if agent.last_seen is not None:
                # Agent is still offline after grace period - mark as disconnected
                await database_sync_to_async(agent.mark_disconnected)()
        except DatabaseError:
            logger.error("Database error during grace period disconnect", exc_info=True)
