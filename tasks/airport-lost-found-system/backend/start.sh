#!/bin/sh
set -e

if [ "${RUN_MIGRATIONS_ON_STARTUP:-false}" = "true" ]; then
  alembic upgrade head
fi

if [ "${RUN_SEED_ON_STARTUP:-false}" = "true" ]; then
  python -m app.scripts.seed
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
