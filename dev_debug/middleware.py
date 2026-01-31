import logging
import re
from typing import Any, Callable

from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


class AgentMessageSnifferMiddleware:
    """
    ASGI middleware that intercepts messages coming from the Agent to the AgentConsumer.
    Valid only when DEBUG is True.
    """

    def __init__(self, inner: Any):
        self.inner = inner
        # Path pattern to match /ws/agent/<agent_key>/
        self.path_regex = re.compile(r"^/ws/agent/(?P<agent_key>[^/]+)/$")

    async def __call__(
        self, scope: dict[str, Any], receive: Callable, send: Callable
    ) -> Any:
        # We only care about WebSockets
        if scope["type"] != "websocket":
            return await self.inner(scope, receive, send)

        # Check if the path matches the agent connection path
        match = self.path_regex.match(scope["path"])
        if not match:
            return await self.inner(scope, receive, send)

        agent_key = match.group("agent_key")
        debug_group_name = f"agent_debug_{agent_key}"
        channel_layer = get_channel_layer()

        # Define a wrapper for the receive function
        async def receive_wrapper() -> dict[str, Any]:
            message = await receive()

            # If it's a websocket.receive (client message to server)
            if message.get("type") == "websocket.receive":
                text_data = message.get("text")
                bytes_data = message.get("bytes")

                try:
                    # Broadcast the sniffed message to the debug group
                    if channel_layer:
                        payload = {
                            "type": "agent.debug_message",
                            "agent_key": agent_key,
                            "text": text_data,
                            "bytes": bytes_data.hex() if bytes_data else None,
                        }
                        await channel_layer.group_send(debug_group_name, payload)
                except Exception as e:
                    logger.error(f"Error in AgentMessageSnifferMiddleware: {e}")

            return message

        # Call the inner application with our wrapped receive
        return await self.inner(scope, receive_wrapper, send)
