#!/usr/bin/env bash
set -euo pipefail

compose_file="${COMPOSE_FILE:-docker-compose.yml}"

python3 - "$compose_file" <<'PY'
import re
import sys

path = sys.argv[1]
text = open(path, encoding='utf-8').read()
pattern = re.compile(r'(image:\s*lissy93/dashy:)[^\s]+')
new, count = pattern.subn(r'\g<1>latest', text, count=1)
if count != 1:
    raise SystemExit('image not found: lissy93/dashy')
open(path, 'w', encoding='utf-8').write(new)
PY

echo "Dashy: latest"
