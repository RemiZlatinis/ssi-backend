import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import Agent, Service


class AgentConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer that handles connections from agents.
    """

    GROUP_NAME = "agent_status"

    async def connect(self):
        """
        Handles a new WebSocket connection.
        Authenticates the agent based on the key in the URL.
        """
        self.agent_key = self.scope["url_route"]["kwargs"]["agent_key"]
        self.agent = await self.get_agent(self.agent_key)

        if self.agent is None:
            await self.close()
        else:
            print(f"Agent '{self.agent.name}' connected successfully.")
            await self.accept()
            # Add agent to the group
            await self.channel_layer.group_add(self.GROUP_NAME, self.channel_name)  # type: ignore
            # Broadcast that this agent is now connected
            await self.channel_layer.group_send(  # type: ignore
                self.GROUP_NAME,
                {
                    "type": "agent.status.update",
                    "agent_id": str(self.agent.id),
                    "agent_name": self.agent.name,
                    "status": "connected",
                },
            )

    async def disconnect(self, code):
        """
        Called when the WebSocket connection is closed.
        """
        if hasattr(self, "agent") and self.agent:
            print(f"Agent '{self.agent.name}' disconnected.")
            # Broadcast that this agent has disconnected
            await self.channel_layer.group_send(  # type: ignore
                self.GROUP_NAME,
                {
                    "type": "agent.status.update",
                    "agent_id": str(self.agent.id),
                    "agent_name": self.agent.name,
                    "status": "disconnected",
                },
            )
            # Remove agent from the group
            await self.channel_layer.group_discard(self.GROUP_NAME, self.channel_name)  # type: ignore
        else:
            print("An unauthenticated agent disconnected.")

    async def agent_status_update(self, event):
        """
        Handler for status update messages. This consumer broadcasts the updates
        but does not need to process them itself. This method is here to
        prevent a "No handler" error when the consumer receives its own message.
        """
        pass

    async def receive(self, text_data=None, bytes_data=None):
        """
        Receives a message from the agent, determines its type,
        and delegates to the appropriate handler.
        """
        if not text_data:
            return

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
                print(f"Received unknown event type: {event_type}")

        except json.JSONDecodeError:
            print(f"Received non-JSON message from {self.agent.name}: {text_data}")
        except Exception as e:
            print(f"Error processing message from {self.agent.name}: {e}")

    # --- Event Handlers ---

    async def _handle_agent_hello(self, event_data):
        """Synchronizes all services from the agent with the database."""
        print(f"Processing 'agent_hello' from {self.agent.name}")
        services_info = event_data.get("services", [])
        await self.sync_services_db(self.agent, services_info)

    async def _handle_service_added(self, event_data):
        """Adds a single new service to the database."""
        service_info = event_data.get("service")
        if service_info:
            print(f"Processing 'service_added' for {service_info.get('name')}")
            await self.add_or_update_service_db(self.agent, service_info)

    async def _handle_service_removed(self, event_data):
        """Removes a single service from the database."""
        service_id = event_data.get("service_id")
        if service_id:
            print(f"Processing 'service_removed' for ID {service_id}")
            await self.remove_service_db(self.agent, service_id)

    async def _handle_status_update(self, event_data):
        """Updates the status of a single service."""
        update = event_data.get("update")
        if update:
            print(
                f"Processing 'status_update' for service ID {update.get('service_id')}"
            )
            await self.update_service_status_db(self.agent, update)

    # --- Database Operations (wrapped for async context) ---

    @database_sync_to_async
    def sync_services_db(self, agent, services_info):
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
    def add_or_update_service_db(self, agent, service_info):
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
    def remove_service_db(self, agent, service_id):
        """Removes a single service."""
        Service.objects.filter(agent=agent, agent_service_id=service_id).delete()

    @database_sync_to_async
    def update_service_status_db(self, agent, update_data):
        """Updates the last known status of a service."""
        try:
            service = Service.objects.get(
                agent=agent, agent_service_id=update_data["service_id"]
            )
            service.last_status = update_data["status"]
            service.last_message = update_data["message"]
            service.last_seen = update_data["timestamp"]
            service.save()
        except Service.DoesNotExist:
            print(
                f"Warning: Received status update for unknown service ID "
                f"{update_data['service_id']} from agent {agent.name}"
            )

    @database_sync_to_async
    def get_agent(self, key):
        """
        Asynchronously fetches the agent from the database.
        """
        try:
            return Agent.objects.get(
                key=key, registration_status=Agent.RegistrationStatus.REGISTERED
            )
        except Agent.DoesNotExist:
            print(f"Connection attempt with invalid agent key: {key}")
            return None
