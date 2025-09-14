# Plan: Send Full Service Data via Server-Sent Events (SSE)

This document outlines the plan to enhance the existing SSE endpoint to broadcast not only agent connection status but also detailed, real-time updates for each of their services.

## Rationale

Providing full service data allows a client-side dashboard to display a rich, live view of the entire system's health without needing to make additional API calls. While this increases the amount of data sent over the SSE connection, the benefits of a real-time, comprehensive view are significant. The implementation will be optimized to ensure it remains efficient.

## Implementation Steps

### 1. Update `AgentConsumer` to Broadcast Service Updates

The `AgentConsumer` is the entry point for all data coming from an agent. It will be modified to broadcast service-specific updates to a channel group.

**File:** `core/consumers.py`

- **Modify `_handle_status_update`:** After successfully processing a `status_update` event from an agent and saving it to the database, the method will be enhanced.
- **Broadcast a new event:** It will send a new message to the `agent_status` group with the type `service.status.update`.
- **Payload:** The message payload will contain the `agent_id` and a dictionary of the updated service's details, including `id`, `agent_service_id`, `last_status`, `last_message`, and `last_seen`.
- **Return Value:** The corresponding database method (`update_service_status_db`) will be modified to return the updated `Service` instance so its data can be broadcast.

### 2. Enhance the SSE View for Rich Data

The SSE view is responsible for streaming data to the browser. It will be upgraded to handle the new service update events and to provide a much richer initial state.

**File:** `core/views.py`

- **Update `get_all_agent_statuses`:**
  - This function will be rewritten to fetch all registered agents and all of their associated services.
  - **Optimization:** It will use Django's `prefetch_related("services")` to prevent the "N+1 query" problem, ensuring that all services for all agents are fetched in just two database queries.
  - The response will be a structured JSON object containing a list of agents, where each agent object contains a list of its services and their last known states.
- **Update `sse_agent_status` View:**
  - The `event_stream` async generator will be modified to handle multiple event types.
  - It will listen for both `agent.status.update` (for agent connect/disconnect) and the new `service.status.update`.
  - A `type` field will be added to the JSON payload of each SSE message (`agent_status`, `service_status`, `initial_state`) so the client-side JavaScript can easily distinguish between different kinds of updates.

### 3. (Optional) Update Frontend JavaScript

The client-side code (e.g., in `status_test.html`) will need to be updated to parse the new, richer JSON structure. It should be able to:

- Handle the `initial_state` message to render the full list of agents and their services.
- Handle `agent_status` updates to toggle the connection status of an agent.
- Handle `service_status` updates to find the specific service (by ID) and update its status, message, and last seen timestamp in the UI.
