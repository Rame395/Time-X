#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
exec "$DIR/venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8000 --workers 2
