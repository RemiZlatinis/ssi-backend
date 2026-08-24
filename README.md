# SSI Backend

The central backend server for the Service Status Indicator (SSI) ecosystem.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

## 📖 Overview

The **SSI Backend** is a Django-based application that serves as the central hub for the SSI monitoring system. It handles:

- **Agent Registration**: Securely onboarding new monitoring agents.
- **Real-time Status**: receiving WebSocket updates from agents.
- **API**: Serving data to the mobile and web clients.
- **Authentication**: Managing user accounts and permissions.

## 🚀 Getting Started

> **Tip:** if you're setting up the whole SSI ecosystem (agent, backend, clients) rather than just this repo, use the [workspace setup script](https://github.com/RemiZlatinis/ssi) in the metarepository instead — it automates everything below across all components.

### Prerequisites

- Python 3.12+
- Poetry (for dependency management)
- Docker/Podman & Compose (for Postgres/Redis)

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/RemiZlatinis/ssi-backend.git
   cd ssi-backend
   ```

2. **Install dependencies**

   ```bash
   poetry install
   ```

3. **Set up the development environment**

   ```bash
   cp -n .env.development .env
   ```

   > `.env.development` ships with sensible local defaults, including the default admin login (see below). `.env` overrides them for your own tweaks — Compose doesn't require it, since the `db` and `backend` services read `.env.development` directly. For production you'd start from the `.env.example` template instead and fill in real values — see [Self-Hosting](./docs/self-hosting.md).

4. **Run services (Database & Redis)**

   ```bash
   docker compose up -d # This could `be docker-compose` or `podman-compose` or `podman compose` depending on your setup.
   ```

   This also starts the Django dev server itself — the `backend` service's image runs `manage.py runserver` with your working directory bind-mounted for hot reload, and publishes port 8000. There's no separate "start the server" step.

5. **Run migrations and create the default admin user**

   `db` and `valkey` don't publish any ports, so they're only reachable from *inside* the Compose network — run one-off Django commands via `docker compose exec`, not directly with `poetry run` on your host:

   ```bash
   docker compose exec backend poetry run python manage.py migrate
   docker compose exec backend poetry run python manage.py ensure_superuser
   ```

   `ensure_superuser` reads `DJANGO_SUPERUSER_USERNAME` / `_EMAIL` / `_PASSWORD` from your `.env` and creates that user if it doesn't already exist yet (safe to re-run).

### Default admin login (development only)

`.env.development` ships with a default admin account so you don't have to create one by hand:

| Field    | Value                                       |
| -------- | -------------------------------------------- |
| URL      | <http://localhost:8000/admin>                 |
| Username | `admin`                                      |
| Password | `admin`                                      |

> ⚠️ These credentials are for local development only and are **not** used in `docker-compose.prod.yml` — production deployments must set their own `DJANGO_SUPERUSER_*` values via real secrets.

## 📚 Documentation

- [Self-Hosting Guide](./docs/self-hosting.md)
- [Authentication](./docs/authentication.md)

## 🤝 Contributing

Please read the contributing guidelines in the [SSI Metarepository](https://github.com/RemiZlatinis/ssi).

## ⚖️ License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.
