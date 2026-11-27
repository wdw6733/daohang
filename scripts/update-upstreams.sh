#!/usr/bin/env bash
set -euo pipefail

compose_file="${COMPOSE_FILE:-docker-compose.yml}"

api() {
  curl -fsSL \
    -H 'Accept: application/vnd.github+json' \
    -H 'X-GitHub-Api-Version: 2022-11-28' \
    "$1"
}

latest_tag() {
  local repo="$1"
  local pattern="$2"
  api "https://api.github.com/repos/${repo}/tags?per_page=100" \
    | jq -r '.[].name' \
    | grep -E "$pattern" \
    | sort -V \
    | tail -n 1
}

replace_image() {
  local image="$1"
  local tag="$2"
  python3 - "$compose_file" "$image" "$tag" <<'PY'
import re
import sys

path, image, tag = sys.argv[1:4]
text = open(path, encoding='utf-8').read()
pattern = re.compile(r'(image:\s*' + re.escape(image) + r':)[^\s]+')
new, count = pattern.subn(r'\g<1>' + tag, text, count=1)
if count != 1:
    raise SystemExit(f'image not found: {image}')
open(path, 'w', encoding='utf-8').write(new)
PY
}

dashy_tag="$(latest_tag 'Lissy93/dashy' '^v?[0-9]+\.[0-9]+\.[0-9]+$')"
dashy_tag="${dashy_tag#v}"

test -n "$dashy_tag"

replace_image 'lissy93/dashy' "$dashy_tag"

echo "Dashy: $dashy_tag"
