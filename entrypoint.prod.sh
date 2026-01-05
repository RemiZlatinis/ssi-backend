#!/bin/sh
# entrypoint.prod.sh

set -e

# Wait for database to be ready
echo "Waiting for database to be ready..."
until python manage.py healthcheck; do
  >&2 echo "Database is unavailable - sleeping"
  sleep 1
done

>&2 echo "Database is up - continuing"

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Create superuser if it doesn't exist (idempotent)
echo "Checking for initial superuser..."
python manage.py createsuperuser --noinput || true

# Start the application
exec "$@"
