#!/usr/bin/env sh
# One-time setup on Linux, macOS or Raspberry Pi OS. Needs Python 3.11+ and Node.js 20+.
set -e
cd "$(dirname "$0")/.."
python3 -m venv backend/.venv
backend/.venv/bin/pip install --upgrade pip >/dev/null
backend/.venv/bin/pip install -e "backend[postgres]"
(cd frontend && npm ci && npm run build)
if [ ! -f .env ]; then
  cp .env.example .env
  SECRET=$(backend/.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(48))")
  sed -i.bak "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET|" .env && rm -f .env.bak
  echo "Created .env with a random SECRET_KEY."
fi
echo "Done. Start ClassPulse with: scripts/start.sh"
