#!/usr/bin/env bash

set -e

# Initialize and run migrations
echo "Initializing..."
python manage.py wait_for_db

# Run migrations
echo "Running migrations..."
python manage.py migrate

# Create a superuser if it doesn't exist
if [ -z "$DJANGO_SUPERUSER_PASSWORD" ] || [ -z "$DJANGO_SUPERUSER_EMAIL" ]; then
    echo "Superuser credentials are not fully set. Skipping superuser creation."
else
    echo "Creating superuser..."
    python manage.py createsuperuser --noinput || echo "Superuser already exists. Skipping creation."
fi

# Start the application
echo "Running Application. Visit admin page at http://localhost:$APPLICATION_PORT/admin"
python manage.py runserver 0.0.0.0:$APPLICATION_PORT