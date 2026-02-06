# Self-Hosting Guide

This guide provides step-by-step instructions for hosting your own instance of the SSI Backend.

## Prerequisites

Before you begin, ensure you have the following installed on your system:

- **Docker & Docker Compose**: Recommended for managing dependencies like Postgres and Redis.
- **Python 3.12+**: Required if you plan to run the server directly or build from source.
- **Poetry**: Used for dependency management and local development.

## Quick Start (Docker Compose)

The easiest way to get started is by using the provided `docker-compose.yml` file.

1. **Clone the repository**:

   ```bash
   git clone https://github.com/RemiZlatinis/ssi-backend.git
   cd ssi-backend
   ```

2. **Configure Environment Variables**:
   Copy the example environment file and edit it with your settings:

   ```bash
   cp .env.example .env
   ```

   _Key variables to set:_
   - `SECRET_KEY`: A unique, long, random string.
   - `SQL_PASSWORD`: Database password.
   - `CORS_ALLOWED_ORIGINS`: Origins allowed to access the API (e.g., your frontend URL).

3. **Start the Services**:

   ```bash
   docker-compose up -d
   ```

   This will start:
   - **Postgres**: Database for storing configuration and status history.
   - **Valkey (Redis)**: Message broker for real-time updates and task queue.
   - **SSI Backend**: The core Django application.

4. **Run Migrations**:
   The containers will automatically run migrations on startup through the entrypoint script.

## Authentication Setup

Currently, SSI Backend supports authentication via **Google OAuth2**. Support for email/password authentication is planned for a future release if requested.

### 1. Create Google OAuth Credentials

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Create a new project (or select an existing one).
3.  Go to **APIs & Services > Credentials**.
4.  Click **Create Credentials > OAuth client ID**.
5.  Select **Web application** as the application type.
6.  Add your backend URL to **Authorized redirect URIs**. The redirect URI pattern is:
    `https://your-backend-domain.com/api/auth/google/login/callback/`
7.  Note down your `Client ID` and `Client Secret`.

### 2. Configure Social Application in Django Admin

After starting the SSI Backend and running migrations, you need to register your Google Client in the database.

1.  Access the Django Admin panel at `https://your-backend-domain.com/admin/`.
2.  Login with a superuser account (Create one using `python manage.py createsuperuser` or via `docker exec`).
3.  Under the **Social Accounts** section, click on **Social applications**.
4.  Click **Add social application**.
5.  Fill in the details:
    - **Provider**: Google
    - **Name**: SSI Google Auth (or any descriptive name)
    - **Client id**: Your Google Client ID
    - **Secret key**: Your Google Client Secret
6.  Select your site from **Chosen sites** (usually `example.com` by default, but you should update the Site name/domain in the **Sites** section first).
7.  Save the application.

## Production Deployment

For production environments, it is recommended to use the optimized production Docker image.

### Building the Production Image

We provide a `Dockerfile.prod` and a helper script `build-prod.sh` (or `build-prod.bat` on Windows) to build a smaller, more secure image.

```bash
# On Linux/macOS
./build-prod.sh

# On Windows (native)
build-prod.bat
```

This will create an image tagged as `ssi-backend:prod`.

### Running in Production

Use the `docker-compose.prod.yml` file for production deployments:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Security Considerations

- **Reverse Proxy**: Always run the SSI Backend behind a reverse proxy like Nginx or Caddy to handle SSL/TLS termination.
- **Environment Secrets**: Ensure `.env` files are not committed to version control and are stored securely.
- **Database Backups**: Implement regular backups for the Postgres database. We include a `dbbackup_admin` app that can be configured for automated backups.

## Manual Installation (No Docker)

If you prefer to run the backend natively:

1. **Install Dependencies**:

   ```bash
   poetry install
   ```

2. **Configure Services**:
   Ensure you have Postgres and Redis/Valkey running locally and accessible.

3. **Run Migrations & Start**:
   ```bash
   poetry run python manage.py migrate
   poetry run python manage.py runserver
   ```

> [!IMPORTANT]
> When running natively, ensure the environment variables in `.env` correctly point to your local service instances.
