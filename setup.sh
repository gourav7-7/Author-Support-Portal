#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -f .env ]; then cp .env.example .env; fi
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
(cd frontend && npm ci && npm run build)
(cd backend && ../.venv/bin/python -m app.seed)
echo 'Setup complete. Add OPENAI_API_KEY to .env, then run: cd backend && ../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000'
