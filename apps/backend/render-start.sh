#!/usr/bin/env bash
set -e

export PATH="$HOME/.local/bin:$PATH"

uv run alembic upgrade head
exec uv run uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
