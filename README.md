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

### Prerequisites

- Python 3.12+
- Docker & Docker Compose (for Redis/Postgres)
- Poetry (for dependency management)

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

3. **Set up environment**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run services (Database & Redis)**

   ```bash
   docker-compose up -d
   ```

5. **Run migrations**

   ```bash
   poetry run python manage.py migrate
   ```

6. **Start the server**
   ```bash
   poetry run python manage.py runserver
   ```

## 📚 Documentation

- [Self-Hosting Guide](./docs/self-hosting.md)

## 🤝 Contributing

Please read the contributing guidelines in the [SSI Metarepository](https://github.com/RemiZlatinis/ssi).

## ⚖️ License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.
