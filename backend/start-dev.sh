#!/usr/bin/env bash

cd "$(dirname "$0")"

source .venv/bin/activate && \
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --workers 1
