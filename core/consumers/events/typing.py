from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel


class ServiceStatus(str, Enum):
    OK = "OK"
    UPDATE = "UPDATE"
    WARNING = "WARNING"
    FAILURE = "FAILURE"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"

    def __str__(self) -> str:
        return self.value


# --- Models ---


class AgentServiceDataModel(BaseModel):
    id: str  # This is the human readable service-id
    name: str
    description: str
    version: str
    schedule: str


class ClientServiceDataModel(AgentServiceDataModel):
    last_message: str
    last_seen: datetime | None
    last_status: ServiceStatus


class ClientAgentDataModel(BaseModel):
    id: str
    name: str
    registration_status: Literal["pending", "registered", "unregistered"]
    services: list[ClientServiceDataModel]
    ip_address: str | None
    is_online: bool
    last_seen: datetime | None


# --- Payloads ---


class AgentReadyPayload(BaseModel):
    services: list[AgentServiceDataModel]


class AgentServiceAddedPayload(BaseModel):
    service: AgentServiceDataModel


class AgentServiceRemovedPayload(BaseModel):
    service_id: str


class AgentServiceStatusUpdatePayload(BaseModel):
    service_id: str
    status: ServiceStatus
    message: str
    timestamp: datetime


class ClientInitialStatusPayload(BaseModel):
    agents: list[ClientAgentDataModel]


class ClientStatusUpdatePayload(BaseModel):
    agent: ClientAgentDataModel


class ClientServiceAddedPayload(BaseModel):
    agent_id: str
    service: ClientServiceDataModel


class ClientServiceRemovedPayload(BaseModel):
    agent_id: str
    service_id: str


class ClientServiceStatusUpdatePayload(BaseModel):
    agent_id: str
    service_id: str
    status: ServiceStatus
    message: str
    timestamp: datetime


# --- Event Models ---


class AgentReadyEvent(BaseModel):
    type: Literal["agent.ready"] = "agent.ready"
    data: AgentReadyPayload


class AgentServiceAddedEvent(BaseModel):
    type: Literal["agent.service_added"] = "agent.service_added"
    data: AgentServiceAddedPayload


class AgentServiceRemovedEvent(BaseModel):
    type: Literal["agent.service_removed"] = "agent.service_removed"
    data: AgentServiceRemovedPayload


class AgentServiceStatusUpdateEvent(BaseModel):
    type: Literal["agent.service_status_update"] = "agent.service_status_update"
    data: AgentServiceStatusUpdatePayload


AgentEvent = (
    AgentReadyEvent
    | AgentServiceAddedEvent
    | AgentServiceRemovedEvent
    | AgentServiceStatusUpdateEvent
)


class ClientInitialStatusEvent(BaseModel):
    type: Literal["client.initial_status"] = "client.initial_status"
    data: ClientInitialStatusPayload


class ClientStatusUpdateEvent(BaseModel):
    type: Literal["client.status_update"] = "client.status_update"
    data: ClientStatusUpdatePayload


class ClientServiceAddedEvent(BaseModel):
    type: Literal["client.service_added"] = "client.service_added"
    data: ClientServiceAddedPayload


class ClientServiceRemovedEvent(BaseModel):
    type: Literal["client.service_removed"] = "client.service_removed"
    data: ClientServiceRemovedPayload


class ClientServiceStatusUpdateEvent(BaseModel):
    type: Literal["client.service_status_update"] = "client.service_status_update"
    data: ClientServiceStatusUpdatePayload


ClientEvent = (
    ClientInitialStatusEvent
    | ClientStatusUpdateEvent
    | ClientServiceAddedEvent
    | ClientServiceRemovedEvent
    | ClientServiceStatusUpdateEvent
)
