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

Optional extended body:
- Explain why, not just what
- Reference related issues if applicable
```

**Types**: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `security`, `build`, `ci`, `style` etc.
**Scopes**: App names (`core`, `authentication`, `notifications`) or `api`, `models`, `admin` etc.

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
