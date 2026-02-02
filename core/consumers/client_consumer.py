import asyncio
import logging
import uuid

from channels.generic.http import AsyncHttpConsumer
from pydantic import ValidationError

from authentication.decorators import sse_require_auth
from core.consumers.events import client_event_type_adapter, get_user_agents
from core.consumers.events.typing import (
    ClientInitialStatusEvent,
    ClientInitialStatusPayload,
)
from core.consumers.groups import get_client_group_name

logger = logging.getLogger(__name__)


class ClientConsumer(AsyncHttpConsumer):
    """
    Consumes an HTTP-Stream connection from a client. (Server-Sent Events)

    Unlike WebsocketConsumer, AsyncHttpConsumer does NOT automatically dispatch
    channel layer messages to handler methods. We must actively listen for them
    using channel_layer.receive() within the handle() method.
    """

    user_clients_group_name = None

    @sse_require_auth
    async def handle(self, body):
        # The `@sse_require_auth` sets a valid user or returns HTTP 401 immediately
        user = self.scope["user"]  # type:ignore

        # Setup SSE Headers
        await self.send_headers(
            headers=[
                (b"Content-Type", b"text/event-stream"),
                (b"Cache-Control", b"no-cache"),
                (b"Transfer-Encoding", b"chunked"),
                (b"Connection", b"keep-alive"),
                (b"Access-Control-Allow-Origin", b"*"),
            ]
        )

        # Join User Group
        self.user_clients_group_name = get_client_group_name(user.pk)

        # IMPORTANT: AsyncHttpConsumer doesn't always have a channel_name assigned
        # by the protocol server (Daphne). If it's missing, we generate one
        # to allow us to participate in the channel layer group.
        if not self.channel_name:
            self.channel_name = f"sse_{uuid.uuid4().hex}"

        logger.debug(
            f"SSE [{self.channel_name}] Joining group: {self.user_clients_group_name}"
        )
        await self.channel_layer.group_add(
            self.user_clients_group_name, self.channel_name
        )

        # Send Initial Status
        initial_agents = await get_user_agents(user)
        payload = ClientInitialStatusPayload(agents=initial_agents)
        event = ClientInitialStatusEvent(data=payload)
        await self._send_server_event(event)

        # Main loop: Listen for channel layer messages and dispatch them.
        try:
            while True:
                try:
                    # Wait for a channel layer message with a timeout for heartbeats
                    message = await asyncio.wait_for(
                        self.channel_layer.receive(self.channel_name),
                        timeout=30,
                    )

                    # Dispatch to appropriate handler based on message type
                    # Message type uses dots (e.g., "status_update"), convert to method
                    handler_name = message["type"].replace(".", "_")
                    handler = getattr(self, handler_name, None)
                    if handler:
                        await handler(message)
                    else:
                        logger.warning(
                            f"SSE [{self.channel_name}] No handler for: {handler_name}"
                        )

                except asyncio.TimeoutError:
                    # Send heartbeat comment to keep connection alive
                    await self.send_body(b":heartbeat\n\n", more_body=True)

        except asyncio.CancelledError:
            logger.debug(
                f"SSE [{self.channel_name}] Connection closed (client disconnected)"
            )
        except Exception as e:
            logger.debug(f"SSE [{self.channel_name}] Connection closed: {e}")
        finally:
            # Cleanup: Leave the group
            if self.user_clients_group_name:
                await self.channel_layer.group_discard(
                    self.user_clients_group_name, self.channel_name
                )
            logger.debug(f"SSE [{self.channel_name}] Cleanup complete")

    # --- Channel Layer Message Handlers ---

    async def status_update(self, message: dict) -> None:
        logger.debug(f"SSE [{self.channel_name}] Processing status_update")
        await self._send_server_event(message["event"])

    async def service_added(self, message: dict) -> None:
        logger.debug(f"SSE [{self.channel_name}] Processing service_added")
        await self._send_server_event(message["event"])

    async def service_removed(self, message: dict) -> None:
        logger.debug(f"SSE [{self.channel_name}] Processing service_removed")
        await self._send_server_event(message["event"])

    async def service_status_update(self, message: dict) -> None:
        logger.debug(f"SSE [{self.channel_name}] Processing service_status_update")
        await self._send_server_event(message["event"])

    # --- Helper Methods ---

    async def _send_server_event(self, event) -> None:
        """
        Validates, serializes, and sends a Pydantic Event as a Server-Sent Event.
        """
        try:
            validated_event = client_event_type_adapter.validate_python(event)
            serialized_event = validated_event.model_dump_json()
            body = f"data: {serialized_event}\n\n"

            logger.debug(
                f"SSE [{self.channel_name}] Sending event: {validated_event.type}"
            )
            await self.send_body(body.encode("utf-8"), more_body=True)
        except ValidationError as e:
            logger.error(f"SSE [{self.channel_name}] Validation Error: {e}")
        except Exception as e:
            logger.error(f"SSE [{self.channel_name}] Send Error: {e}")
