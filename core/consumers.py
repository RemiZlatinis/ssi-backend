import json
import logging
import uuid
from typing import Any, Optional

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from notifications.models import Device

from .models import Agent, Service
from .utils import get_client_ip

logger = logging.getLogger("core")


class AgentConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer that handles connections from agents.
    """

    agent: Optional[Agent] = None
    agent_key: Optional[uuid.UUID] = None
    agent_group_name: Optional[str] = None

    async def connect(self) -> None:
        """
        Handles a new WebSocket connection.
        Authenticates the agent based on the key in the URL. The key is validated
        to be a proper UUID.
        """
        # Use .get() for safe dictionary access to satisfy type checkers and prevent
        # potential KeyErrors if the scope is not what we expect.
        agent_key_str = (
            self.scope.get("url_route", {}).get("kwargs", {}).get("agent_key")
        )
        if not agent_key_str:
            logger.warning("Connection attempt with missing agent_key in URL.")
            await self.close()
            return

        try:
            self.agent_key = uuid.UUID(agent_key_str)
        except (ValueError, TypeError):
            # The provided key is not a valid UUID (e.g., "None").
            logger.warning(
                f"Connection attempt with invalid key format: {agent_key_str}"
            )
            await self.close()
            return

        self.agent = await self.get_agent(self.agent_key)

        if self.agent is None:
            # The key was a valid UUID but not found or not registered.
            # get_agent() already prints a message.
            await self.close()
        else:
            logger.info(f"Agent '{self.agent.name}' connected successfully.")
            await self.accept()
            await self._set_online()
            await self._check_and_update_agent_ip()

            # Dynamically define a group name based on the agent's owner
            owner_id = await self._get_agent_owner_id(self.agent)
            self.agent_owner_group_name = f"user_{owner_id}_agent_status_updates"

            if self.channel_layer:
                # 1. Join a unique group for this agent connection. This allows
                #    the backend (e.g., an HTTP view) to send direct messages
                #    to this specific agent, like 'force_disconnect'.
                self.agent_group_name = f"agent_{self.agent_key}"
                await self.channel_layer.group_add(
                    self.agent_group_name, self.channel_name
                )

                # 2. Broadcast the 'online' status to the user-facing group.
                #    This group is listened to by the front-end SSE view to
                #    provide real-time status updates to the user.
                await self._broadcast_agent_status(is_online=True)

    async def disconnect(self, code: int) -> None:
        """
        Called when the WebSocket connection is closed.
        """
        if hasattr(self, "agent") and self.agent:
            logger.info(f"Agent '{self.agent.name}' disconnected.")
            await self._set_offline()
            if hasattr(self, "channel_layer") and self.channel_layer:
                # Discard from agent-specific group
                if hasattr(self, "agent_group_name"):
                    await self.channel_layer.group_discard(
                        self.agent_group_name, self.channel_name
                    )
                # Broadcast the offline status to the user's group
                await self._broadcast_agent_status(is_online=False)
        else:
            logger.info("An unauthenticated agent disconnected.")

    async def receive(
        self, text_data: str | None = None, bytes_data: bytes | None = None
    ) -> None:
        """
        Receives a message from the agent, determines its type,
        and delegates to the appropriate handler.
        """
        if not text_data or not self.agent:
            return

        # On every message, check if the agent's IP has changed and update it.
        await self._check_and_update_agent_ip()

        try:
            data = json.loads(text_data)
            event_type = data.get("event")

            if event_type == "agent_hello":
                await self._handle_agent_hello(data)
            elif event_type == "service_added":
                await self._handle_service_added(data)
            elif event_type == "service_removed":
                await self._handle_service_removed(data)
            elif event_type == "status_update":
                await self._handle_status_update(data)
            else:
                logger.warning(f"Received unknown event type: {event_type}")

        except json.JSONDecodeError:
            logger.warning(
                f"Received non-JSON message from {self.agent.name}: {text_data}"
            )
        except Exception as e:
            logger.error(
                f"Error processing message from {self.agent.name}: {e}", exc_info=True
            )

    # --- Event Handlers ---

    async def force_disconnect(self, event: dict[str, Any]) -> None:
        """
        Handler for the 'force.disconnect' event.
        Closes the WebSocket connection with a custom code.
        """
        if not self.agent:
            return
        logger.info(
            f"Forcibly disconnecting agent {self.agent.name} due to unregistration."
        )
        # 4001 is a custom code indicating the agent was unregistered.
        await self.close(code=4001)

    async def _handle_agent_hello(self, event_data: dict[str, Any]) -> None:
        """Synchronizes all services from the agent with the database."""
        if not self.agent:
            return
        logger.info(f"Processing 'agent_hello' from {self.agent.name}")
        services_info = event_data.get("services", [])
        await self.update_last_seen()
        await self.sync_services_db(self.agent, services_info)

    async def _handle_service_added(self, event_data: dict[str, Any]) -> None:
        """Adds a single new service to the database."""
        service_info = event_data.get("service")
        if service_info:
            logger.info(f"Processing 'service_added' for {service_info.get('name')}")
            await self.update_last_seen()
            await self.add_or_update_service_db(self.agent, service_info)
            # After adding/updating service, broadcast an update to the user's group
            await self._broadcast_service_added(service_info)

    async def _handle_service_removed(self, event_data: dict[str, Any]) -> None:
        """Removes a single service from the database."""
        service_id = event_data.get("service_id")
        if service_id:
            logger.info(f"Processing 'service_removed' for ID {service_id}")
            await self.update_last_seen()
            await self.remove_service_db(self.agent, service_id)
            # After removing service, broadcast an update to the user's group
            await self._broadcast_service_removed(service_id)

    async def _handle_status_update(self, event_data: dict[str, Any]) -> None:
        """Updates the status of a single service."""
        update = event_data.get("update")
        if update:
            logger.info(
                f"Processing 'status_update' for service ID {update.get('service_id')}"
            )
            await self.update_last_seen()
            await self.update_service_status_db(self.agent, update)
            # After updating service status, broadcast an update to the user's group
            await self._broadcast_service_status_update(update)

    # --- Broadcasting Methods ---

    async def _broadcast_agent_status(self, is_online: bool) -> None:
        """Sends an agent online/offline status update to the channel layer group."""
        if hasattr(self, "channel_layer") and self.channel_layer and self.agent:
            await self.channel_layer.group_send(
                self.agent_owner_group_name,
                {
                    "type": "agent.status.update",
                    "agent_id": str(self.agent.pk),
                    "agent_name": self.agent.name,
                    "is_online": is_online,
                },
            )

    async def _broadcast_service_status_update(self, update_data: dict) -> None:
        """Sends a service status update to the channel layer group."""
        if hasattr(self, "channel_layer") and self.channel_layer and self.agent:
            await self.channel_layer.group_send(
                self.agent_owner_group_name,
                {
                    "type": "service.status.update",
                    "agent_id": str(self.agent.pk),
                    "agent_name": self.agent.name,
                    "service_id": update_data.get("service_id"),
                    "status": update_data.get("status", "UNKNOWN"),
                    "message": update_data.get("message", ""),
                    # TODO: Move all the timestamp logic to the backend
                    "timestamp": update_data.get("timestamp"),
                },
            )

    async def _broadcast_service_removed(self, service_id: str) -> None:
        """Sends a service removed event to the channel layer group."""
        if hasattr(self, "channel_layer") and self.channel_layer and self.agent:
            await self.channel_layer.group_send(
                self.agent_owner_group_name,
                {
                    "type": "service.removed",
                    "agent_id": str(self.agent.pk),
                    "agent_name": self.agent.name,
                    "service_id": service_id,
                },
            )

    async def _broadcast_service_added(self, service_info: dict) -> None:
        """Sends a service added/updated event to the channel layer group."""
        if hasattr(self, "channel_layer") and self.channel_layer and self.agent:
            await self.channel_layer.group_send(
                self.agent_owner_group_name,
                {
                    "type": "service.added",
                    "agent_id": str(self.agent.pk),
                    "agent_name": self.agent.name,
                    "service_id": service_info.get("id"),
                    "name": service_info.get("name"),
                    "description": service_info.get("description"),
                    "version": service_info.get("version"),
                    "schedule": service_info.get("schedule"),
                    # Initial status for a newly added service
                    "last_status": "UNKNOWN",
                    "last_message": "",
                    "last_seen": None,  # Will be updated on first status report
                },
            )

    # --- Database Operations (wrapped for async context) ---

    @database_sync_to_async
    def _update_agent_ip_in_db(self, new_ip: str | None) -> None:
        """
        Updates the agent's IP address in the database.
        This method is designed to be called from an async context.
        """
        if not self.agent:
            return
        self.agent.ip_address = new_ip
        self.agent.save(update_fields=["ip_address"])
        logger.info(f"Updated IP address for agent '{self.agent.name}' to {new_ip}")

    async def _check_and_update_agent_ip(self) -> None:
        """
        Checks if the agent's IP has changed and updates it in the DB if so.
        """
        if not self.agent:
            return
        current_ip = get_client_ip(self.scope)
        # Only hit the DB if the IP is new and different from the last known one.
        if current_ip and self.agent.ip_address != current_ip:
            await self._update_agent_ip_in_db(current_ip)

    @database_sync_to_async
    def _set_online(self) -> None:
        """Set the agent as online and send push notification."""
        if not self.agent:
            return
        self.agent.mark_connected()

        # Send notification
        user = self.agent.owner
        user_devices = Device.objects.filter(user=user, status=Device.STATUS_ACTIVE)
        for device in user_devices:
            device.send_notification(title=f"Agent '{self.agent.name}' is now online")

    @database_sync_to_async
    def _set_offline(self) -> None:
        """Set the agent as offline and send push notification."""
        if not self.agent:
            return
        self.agent.mark_disconnected()

        # Send notification
        user = self.agent.owner
        user_devices = Device.objects.filter(user=user, status=Device.STATUS_ACTIVE)
        for device in user_devices:
            device.send_notification(title=f"Agent '{self.agent.name}' is now offline")

    @database_sync_to_async
    def update_last_seen(self) -> None:
        """Updates the agent's last_seen timestamp."""
        if not self.agent:
            return
        self.agent.update_last_seen()

    @database_sync_to_async
    def sync_services_db(
        self, agent: Agent, services_info: list[dict[str, Any]]
    ) -> None:
        """Full sync: update/create services from the list, remove any not present."""
        incoming_service_ids = {s["id"] for s in services_info}

        # Update or create services sent by the agent
        for service_data in services_info:
            Service.objects.update_or_create(
                agent=agent,
                agent_service_id=service_data["id"],
                defaults={
                    "name": service_data["name"],
                    "description": service_data["description"],
                    "version": service_data["version"],
                    "schedule": service_data["schedule"],
                },
            )

        # Remove services that are in the DB but were not in the hello message
        agent.services.exclude(agent_service_id__in=incoming_service_ids).delete()

    @database_sync_to_async
    def add_or_update_service_db(
        self, agent: Agent, service_info: dict[str, Any]
    ) -> None:
        """Creates or updates a single service."""
        Service.objects.update_or_create(
            agent=agent,
            agent_service_id=service_info["id"],
            defaults={
                "name": service_info["name"],
                "description": service_info["description"],
                "version": service_info["version"],
                "schedule": service_info["schedule"],
            },
        )

    @database_sync_to_async
    def remove_service_db(self, agent: Agent, service_id: str) -> None:
        """Removes a single service."""
        Service.objects.filter(agent=agent, agent_service_id=service_id).delete()

    @database_sync_to_async
    def update_service_status_db(
        self, agent: Agent, update_data: dict[str, Any]
    ) -> None:
        """Updates the last known status of a service."""
        try:
            # Use get() to fetch the instance, which is necessary to trigger signals.
            service = Service.objects.get(
                agent=agent, agent_service_id=update_data["service_id"]
            )
            # Update the fields on the instance
            service.last_status = update_data.get("status", "UNKNOWN")
            service.last_message = update_data.get("message", "")
            # TODO: Move all the timestamp logic to the backend
            service.last_seen = update_data.get("timestamp")

            # Call save() and specify which fields to update for efficiency.
            # This will now correctly trigger the pre_save and post_save signals.
            service.save(update_fields=["last_status", "last_message", "last_seen"])
        except Service.DoesNotExist:
            logger.warning(
                f"Received status update for unknown service ID "
                f"{update_data.get('service_id')} from agent {agent.name}"
            )

    @database_sync_to_async
    def _get_agent_owner_id(self, agent: Agent) -> int:
        """Asynchronously fetches the owner ID of an agent."""
        return agent.owner.id

    @database_sync_to_async
    def get_agent(self, key: uuid.UUID) -> Agent | None:
        """
        Asynchronously fetches the agent from the database.
        """
        try:
            return Agent.objects.get(
                key=key, registration_status=Agent.RegistrationStatus.REGISTERED
            )
        except Agent.DoesNotExist:
            logger.warning(f"Connection attempt with invalid agent key: {key}")
            return None
