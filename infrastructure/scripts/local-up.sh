#!/usr/bin/env bash
set -euo pipefail
if [ "${MUD_SEED_FIXTURES:-}" != "1" ]; then
  echo "Local test stack only. Explicitly run MUD_SEED_FIXTURES=1 bash infrastructure/scripts/local-up.sh for isolated test assets. See docs/LIVE_SETUP.md for real data." >&2
  exit 1
fi
cd "$(dirname "$0")/../.."
[ -f .env ] || python3 scripts/init-local.py
compose=(docker compose --env-file .env -f infrastructure/docker-compose.yml)
"${compose[@]}" up -d --build postgres redis chain
npm ci --no-audit --no-fund
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.lock
backend/.venv/bin/pip install --no-deps -e backend
npm run compile
backend/.venv/bin/python scripts/generate_merkle_tree.py tests/fixtures/eligibility.dataset.json tests/fixtures/eligibility.local.json
npm run deploy:local
"${compose[@]}" up -d --build
