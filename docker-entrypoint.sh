#!/usr/bin/env bash

set -e

echo "Running migrations..."
python manage.py migrate

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Running Application at http://localhost:$APPLICATION_PORT"
gunicorn -b "0.0.0.0:$APPLICATION_PORT" -w 2 -k uvicorn.workers.UvicornWorker conf.asgi:application
