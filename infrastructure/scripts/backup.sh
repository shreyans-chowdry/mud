#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p runtime/backups
file="runtime/backups/mud-$(date -u +%Y%m%dT%H%M%SZ).dump"
docker compose --env-file .env -f infrastructure/docker-compose.yml exec -T postgres pg_dump -U mud -d mud -Fc > "$file"
printf 'Database backup written to %s\n' "$file"
