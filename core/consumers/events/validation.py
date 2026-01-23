from typing import Annotated

from pydantic import Field, TypeAdapter

from core.consumers.events.typing import AgentEvent, ClientEvent

# The "Discriminated Union" - Pydantic uses 'type' to decide which model to use
AgentEventType = Annotated[AgentEvent, Field("type")]
# and creates an Adapter for Runtime Validation
agent_event_type_adapter = TypeAdapter(AgentEventType)


# Client Events
ClientEventType = Annotated[ClientEvent, Field("type")]
client_event_type_adapter = TypeAdapter(ClientEventType)
