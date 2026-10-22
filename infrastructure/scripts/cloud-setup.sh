#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
node -e "if(Number(process.versions.node.split('.')[0])!==22)throw Error('Select Node 22 in the cloud environment before setup')"
python3 -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11+ required"'
npm ci --no-audit --no-fund
npm --prefix frontend ci --no-audit --no-fund
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.lock
backend/.venv/bin/pip install --no-deps -e backend
npm run compile
printf '%s\n' 'Cloud dependencies installed. No production keys, deployment, seeding or blockchain writes were used.'
