# AGENTS.md — ssi-backend

> **This file takes precedence over README.md when directives conflict.** > **Architectural intent must be preserved over convenience.**

---

## Scope

### What This Repository Is

- Central API and control plane for the SSI monitoring system
- Built with Django 5.x, Django REST Framework, Channels, and PostgreSQL
- Receives status reports from agents, persists data, exposes APIs to clients
- Enforces authentication and trust boundaries
- Sends push notifications for agent status changes (e.g., "agent is offline") to mobile clients

### What This Repository Is NOT

- A user interface or frontend
- A monitoring agent or probe
- A job scheduler or queue worker

### Interacts With

| Component           | Relationship                               |
| ------------------- | ------------------------------------------ |
| `ssi-agent`         | Receives status reports via WebSocket      |
| `ssi-client-mobile` | Serves data via REST API and SSE           |
| `ssi-client-mobile` | Sends push notifications to mobile clients |

---

## Django App Architecture

Follow Django's philosophy: each piece of logic belongs in its best-fit app.

| App              | Purpose                                                                                                    | Reusable |
| ---------------- | ---------------------------------------------------------------------------------------------------------- | :------: |
| `core`           | Domain logic, agent/service models, cross-cutting triggers (e.g., "send notification when status changes") |    ❌    |
| `authentication` | Auth flows, tokens, user management                                                                        |    ✅    |
| `notifications`  | Notification device models, push delivery logic                                                            |    ✅    |
| `project`        | Django project settings, root URLs, ASGI/WSGI config                                                       |    —     |
| Other apps       | Domain-specific reusable logic                                                                             |    ✅    |

### Placement Rules

- **Business logic**: Goes in the app that owns the domain concept
- **Cross-cutting triggers**: Live in `core` (e.g., notification triggers on agent status change)
- **Reusable utilities**: Create a dedicated app or use `core` sparingly

---

## API Contract

### Current State

- **No versioning** — Intentional for rapid early-stage development
- Breaking changes are acceptable during this phase

### Future State

- URL-based versioning (`/api/v1/`, `/api/v2/`) when stability matters
- Header-based versioning is not planned

### Compatibility Rules

- Additive changes (new fields, endpoints) are allowed freely
- Removing or renaming fields requires human approval
- Changing response structure is a breaking change

---

## Security Model

### Authentication

- Token-based authentication for agents
- Session authentication for admin panel
- JWT or similar for mobile clients (via `dj-rest-auth`)

### Trust Boundaries

- Agents are semi-trusted (authenticated, but limited permissions)
- Mobile clients are untrusted (validate all input)
- Admin panel requires staff privileges

### Non-Negotiable Rules

- **Never weaken authentication for convenience**
- **Never expose internal endpoints publicly**
- **Never bypass permission classes**

---

## Non-Negotiables

These technologies and patterns **must not be replaced** without explicit architectural approval:

| Category        | Requirement                        |
| --------------- | ---------------------------------- |
| Framework       | Django 5.x + Django REST Framework |
| Real-time       | Django Channels (WebSocket, SSE)   |
| Database        | PostgreSQL                         |
| Auth            | Token-based for agents             |
| Package manager | Poetry                             |

---

## Forbidden Patterns

AI agents **must not introduce** the following:

| Pattern                                   | Reason                                           |
| ----------------------------------------- | ------------------------------------------------ |
| Business logic in views/viewsets          | Use services, managers, or model methods         |
| Client-specific formatting in serializers | Serializers are data contracts, not presentation |
| Background jobs without approval          | Sprawl risk; requires architectural decision     |
| Direct model access in views              | Always use serializers for data I/O              |
| Raw SQL without justification             | ORM preferred for maintainability                |
| Weakening auth "temporarily"              | Never acceptable                                 |

---

## Change Discipline

| Action                              | Allowed Freely | Requires Approval | Forbidden |
| ----------------------------------- | :------------: | :---------------: | :-------: |
| Add new endpoint                    |       ✅       |                   |           |
| Add serializer field                |       ✅       |                   |           |
| Add model field (nullable)          |       ✅       |                   |           |
| Modify existing serializer behavior |                |        ✅         |           |
| Remove or rename model field        |                |        ✅         |           |
| Change authentication mechanism     |                |        ✅         |           |
| Add new Django app                  |                |        ✅         |           |
| Add external service dependency     |                |        ✅         |           |
| Bypass permission classes           |                |                   |    ❌     |
| Store secrets in code               |                |                   |    ❌     |
| Disable security middleware         |                |                   |    ❌     |
| Manually write Django migrations    |                |                   |    ❌     |

**Why manual migrations are forbidden:**
Manually creating migration files bypasses Django's migration state tracking, causing `FieldDoesNotExist` errors and breaking CI/CD pipelines. Django-generated migrations contain critical internal state updates that hand-written files lack.

**Correct approach:**
Always use Django's `makemigrations` command:
```bash
poetry run python -m manage makemigrations <app_name>
```

**When you need a custom migration** (data migrations, complex schema changes):
1. First run `makemigrations` to generate the base migration
2. Then edit the generated file to add custom operations
3. Never create a migration file from scratch

---

## Development & Contribution

### Pre-Commit Hooks (Required for All Contributors)

This repository uses pre-commit hooks to enforce code quality standards (Black, Ruff, Mypy). **Hooks must be installed immediately after cloning the repository.**

```bash
# Install pre-commit tool
pip install pre-commit

# Initialize hooks for this repository
pre-commit install
```

These hooks will automatically run on staged files during `git commit`. To manually verify all checks before committing:

```bash
# Run all checks on all files
pre-commit run --all-files
```

If hooks fail, fix the reported issues, stage them again, and retry the commit. **Commits that fail pre-commit checks will not be allowed.**

### AI Agent Conduct

When working on this repository, AI agents **must**:

1. Ensure pre-commit hooks are initialized in the development environment before making any commits
2. Verify all pre-commit checks pass locally before proposing changes
3. Never bypass or disable pre-commit hooks
4. Include pre-commit validation in any CI/CD pipeline modifications

---

## Commit Guidelines

**Message Format:**

```
type(scope): short description

Body paragraphs describing the problem and solution

Key changes (only when needed for clarity):
- Specific change 1
- Specific change 2
```

**Types**: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `security`, `build`, `ci`, `style` etc.
**Scopes**: App names (`core`, `authentication`, `notifications`) or `api`, `models`, `admin` etc.

### Writing Effective Commit Messages

A good commit message tells the story of **what the user experiences** and **how we fixed it**, not just what code changed.

**The One-Line Summary:**
- Describe the user-visible impact or symptom, NOT the root technical cause
- Think: "What would a user report as a bug?" not "What was wrong in the code?"
- Use active voice: "prevent", "fix", "add", "remove" — not "fixes", "adds"

**The Body:**
1. **Problem paragraph**: Describe what users experience. Be specific about symptoms and impact.
2. **Solution paragraph**: Explain how the fix addresses the problem. Focus on behavior changes, not implementation details.
3. **Key changes** (optional): Only include for complex changes where the code modifications aren't obvious from the description. List specific files/methods modified when the "what" and "how" aren't enough.

### Examples

#### Good Example — Fix Type

```
fix(core): unnecessary notifications about agent online status

User receives spam notifications every hour when agents briefly disconnect
and reconnect, making it hard to notice genuine outages.

We are introducing a 5-second grace period before marking an agent as
disconnected. If the agent reconnects within this window, no notifications
are sent. Only sustained WebSocket disconnections trigger agent disconnection.

Key changes:
- AgentConsumer.disconnect: Sets last_seen, waits 5s, refreshes from DB,
  and marks agent disconnected after verifying disconnection was sustained
- Agent.mark_disconnected: Now only updates is_online and sends signal
  (last_seen is set in disconnect handler before grace period)
```

#### Bad Example — Same Fix

```
fix(core): fix notification bug

The mark_disconnected method was causing too many notifications. Added a
sleep and check before sending notifications. Also updated the model to
not set last_seen anymore.

Changes:
- Updated disconnect method
- Modified mark_disconnected
- Added refresh_from_db call
```

**Why it's bad**:
- Summary describes nothing about user impact ("fix notification bug" is generic)
- Body focuses on code changes, not user problem
- "Added a sleep" describes implementation, not behavior
- No explanation of WHY the notifications were problematic

#### Good Example — Feature Type

```
feat(api): agents can update service configuration without reconnecting

Previously, agents had to disconnect and reconnect to the WebSocket to
propagate service configuration changes (name, description, schedule) to
the backend. This caused unnecessary connection churn and status flapping.

We now support a new agent.service_updated event that allows agents to
push configuration changes in real-time without disrupting the connection.
The backend validates and applies updates immediately while maintaining
existing service state.

Key changes:
- Add AgentServiceUpdatedEvent type and handler
- Update Service model to support partial updates
- Broadcast service changes to connected clients via SSE
```

#### Bad Example — Same Feature

```
feat(api): add service update endpoint

Added new event type for service updates. Agents can now send updates
without reconnecting. Also added handler and updated the service model.

- Added AgentServiceUpdatedEvent
- Added handle_service_updated function
- Modified Service.save method
```

**Why it's bad**:
- Summary mentions "endpoint" (incorrect terminology for WebSocket events)
- Body just lists what was added, not why it matters
- No mention of the problem (connection churn)
- No mention of the benefit (no disruption)

#### When to Skip "Key Changes"

For simple, obvious fixes, omit the Key Changes section:

```
fix(auth): login fails with case-sensitive email addresses

Users could not log in if they typed their email with different casing
than when they registered (e.g., "User@Example.com" vs "user@example.com").

Email addresses are now normalized to lowercase during both registration
and login, ensuring consistent matching regardless of input casing.
```

**No Key Changes needed** — the fix is obvious from the description (normalize email casing).

### Quick Checklist

- [ ] Does the one-line summary describe what users experience?
- [ ] Does the body explain WHY this change was needed (problem)?
- [ ] Does the body explain WHAT behavior changed (solution)?
- [ ] Are technical implementation details in "Key Changes" only when necessary?
- [ ] Would someone reading this commit in 6 months understand the context?

---

## Performance Expectations

| Aspect                | Expectation                              |
| --------------------- | ---------------------------------------- |
| Read/Write ratio      | Read-heavy (status queries)              |
| Concurrency           | Multiple agents + clients simultaneously |
| Latency               | Sub-second for status endpoints          |
| WebSocket connections | Long-lived, one per agent                |

---

## Explicit Non-Goals

The following are **not responsibilities** of this repository:

- Running monitoring checks (that's `ssi-agent`)
- Rendering UI (that's `ssi-client-mobile` or `ssi-site`)
- Public marketing content (that's `ssi-site`)
- Self-contained offline operation
