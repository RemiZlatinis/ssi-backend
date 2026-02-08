import asyncio
import logging
import uuid

from channels.generic.http import AsyncHttpConsumer
from django.conf import settings
from pydantic import ValidationError

from core.consumers.events import client_event_type_adapter, get_user_agents
from core.consumers.events.typing import (
    ClientInitialStatusEvent,
    ClientInitialStatusPayload,
)
from core.consumers.groups import get_client_group_name, get_user_sse_channel_name

logger = logging.getLogger(__name__)


class ClientConsumer(AsyncHttpConsumer):
    """Server-Sent Events consumer for streaming agent updates to clients."""

    user_clients_group_name = None
    _disconnecting = False

    async def handle(self, body):
        user = self.scope["user"]

        if not user.is_authenticated:
            await self.send_response(
                401,
                b"Authentication required",
                headers=[(b"Content-Type", b"application/json")],
            )
            return

        # CORS headers
        cors_headers = []
        for key, value in self.scope["headers"]:
            if key == b"origin" and value.decode() in settings.CORS_ALLOWED_ORIGINS:
                # Add the validated origin header and credentials header to the response
                cors_headers.append((b"Access-Control-Allow-Origin", value))
                cors_headers.append((b"Access-Control-Allow-Credentials", b"true"))
                break

        # Send SSE headers
        await self.send_headers(
            headers=[
                (b"Content-Type", b"text/event-stream"),
                (b"Cache-Control", b"no-cache"),
                (b"Transfer-Encoding", b"chunked"),
                (b"Connection", b"keep-alive"),
                *cors_headers,
            ]
        )

        # Setup channel and group
        # Use hybrid naming: deterministic prefix + unique suffix per connection
        # This ensures all clients receive messages while keeping channels debuggable
        self.user_clients_group_name = get_client_group_name(user.pk)
        base_channel = get_user_sse_channel_name(user.pk)
        self.channel_name = f"{base_channel}_{uuid.uuid4().hex[:8]}"

        logger.debug(f"SSE [{self.channel_name}] Connected")

        try:
            await self.channel_layer.group_add(
                self.user_clients_group_name, self.channel_name
            )
        except Exception as e:
            logger.error(f"SSE [{self.channel_name}] Failed to join group: {e}")
            return

        # Send initial status
        initial_agents = await get_user_agents(user)
        event = ClientInitialStatusEvent(
            data=ClientInitialStatusPayload(agents=initial_agents)
        )
        await self._send_event(event)

        # Listen for events
        try:
            while not self._disconnecting:
                try:
                    # Wait for a channel layer message with a timeout for heartbeats
                    message = await asyncio.wait_for(
                        self.channel_layer.receive(self.channel_name),
                        timeout=30,
                    )
                    await self._handle_message(message)

                except asyncio.TimeoutError:
                    if not self._disconnecting:
                        # Send heartbeat comment to keep connection alive
                        await self.send_body(b":heartbeat\n\n", more_body=True)

        except asyncio.CancelledError:
            logger.debug(f"SSE [{self.channel_name}] Disconnected")
            self._disconnecting = True
            raise
        finally:
            await self._cleanup()

    async def _handle_message(self, message: dict) -> None:
        """Dispatch message to appropriate handler based on type."""
        handler_name = message["type"].replace(".", "_")
        handler = getattr(self, handler_name, None)

        if handler:
            await handler(message)
        else:
            logger.warning(
                f"SSE [{self.channel_name}] Unknown message type: {handler_name}"
            )

    async def _handle_event(self, message: dict) -> None:
        """Generic handler for all event types."""
        if self._disconnecting:
            return
        await self._send_event(message["event"])

    # Message handlers - all delegate to _handle_event
    status_update = _handle_event
    service_added = _handle_event
    service_removed = _handle_event
    service_status_update = _handle_event

    async def _send_event(self, event) -> None:
        """Send an event to the client."""
        if self._disconnecting:
            return

        try:
            validated_event = client_event_type_adapter.validate_python(event)
            body = f"data: {validated_event.model_dump_json()}\n\n"
            await self.send_body(body.encode("utf-8"), more_body=True)
        except ValidationError as e:
            logger.error(f"SSE [{self.channel_name}] Validation error: {e}")
        except Exception as e:
            logger.error(f"SSE [{self.channel_name}] Send error: {e}")

    async def _cleanup(self) -> None:
        """Leave the group on disconnect."""
        try:
            await self.channel_layer.group_discard(
                self.user_clients_group_name, self.channel_name
            )
        except Exception:
            pass
