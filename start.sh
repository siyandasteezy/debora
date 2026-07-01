#!/bin/bash
set -e

echo "Running database migrations..."
alembic -c alembic/alembic.ini upgrade head

echo "Starting server..."
exec uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1
