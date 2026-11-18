#!/usr/bin/env sh
# Starts ClassPulse on port 8000 (reachable from other devices in the same network).
set -e
cd "$(dirname "$0")/.."
PORT="${PORT:-8000}"
echo "ClassPulse is starting on http://0.0.0.0:$PORT - open it in your browser and follow the hint on screen."
exec backend/.venv/bin/uvicorn classpulse.main:app --app-dir backend --host 0.0.0.0 --port "$PORT" --no-access-log
