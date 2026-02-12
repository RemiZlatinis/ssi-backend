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

    async def disconnect(self, code: int) -> None:
        try:
            if self.agent:
                # Set agent.last_seen immediately
                self.agent.last_seen = timezone.now()
                await database_sync_to_async(self.agent.save)(
                    update_fields=["last_seen"]
                )

                # Wait the agent grace period. Before refetch from database
                if self.agent.grace_period > 0:
                    await asyncio.sleep(self.agent.grace_period)
                    await database_sync_to_async(self.agent.refresh_from_db)()

                    # If the agent.last_seen is changed to None, agent has reconnected.
                    if not self.agent.last_seen:
                        logger.debug(
                            f"Agent {self.agent.pk} reconnected within grace period, "
                            "skipping disconnect notification"
                        )
                        return

                # Mark as disconnected
                await database_sync_to_async(self.agent.mark_disconnected)()
        except DatabaseError:
            logger.error("Database error while disconnecting agent", exc_info=True)
