import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import Agent


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
        Receives a message from the agent and logs it to the terminal.
        """
        if text_data:
            print(f"\n--- Message from Agent '{self.agent.name}' ---")
            try:
                # Pretty-print the JSON data for readability
                data = json.loads(text_data)
                print(json.dumps(data, indent=2))
            except json.JSONDecodeError:
                print("Received non-JSON message:")
                print(text_data)
            print("------------------------------------------\n")

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
