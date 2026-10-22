#!/usr/bin/env python3
"""Generate local credentials without printing secrets or overwriting existing configuration."""
import os
import secrets
from pathlib import Path
root = Path(__file__).resolve().parents[1]
p = root / '.env'
if p.exists():
    raise SystemExit('.env already exists; leaving it unchanged')
password, webhook = secrets.token_hex(24), secrets.token_hex(32)
source = (root / '.env.local.example').read_text().replace('POSTGRES_PASSWORD=\n', f'POSTGRES_PASSWORD={password}\n')
source = source.replace('REPLACE_WITH_GENERATED_LOCAL_PASSWORD', password).replace('MUD_WEBHOOK_SECRET=\n', f'MUD_WEBHOOK_SECRET={webhook}\n')
fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as f:
    f.write(source)
print('Created ignored .env with random local database and webhook credentials')

frontend = root / 'frontend/.env.local'
if not frontend.exists():
    fd = os.open(frontend, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f:
        f.write('NEXT_PUBLIC_API_URL=http://127.0.0.1:8000\nNEXT_PUBLIC_LOCAL_RPC=http://127.0.0.1:8545\nNEXT_PUBLIC_ALLOW_TEST_NETWORKS=true\n')
    print('Created local-only frontend configuration with explicit test-network opt-in')
