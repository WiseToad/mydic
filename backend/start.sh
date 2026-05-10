#!/usr/bin/env bash

cd "$(dirname "$0")"

alembic upgrade head && \
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
