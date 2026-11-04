#!/usr/bin/env bash
# Dump the local development database into db/dumps/.
set -euo pipefail

PROJECT_ROOT="$(dirname "$(dirname "$(realpath "${BASH_SOURCE[0]}")")")"
cd "$PROJECT_ROOT"

label="${1:-$(date +%Y-%m-%d_%H%M)}"
target="db/dumps/${label}.dump"
mkdir -p db/dumps

docker compose up -d --wait db >/dev/null

if ! docker compose exec -T db sh -lc 'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"' > "$target"; then
  rm -f "$target"
  printf 'dump failed; nothing written\n' >&2
  exit 1
fi

if [[ ! -s "$target" ]]; then
  rm -f "$target"
  printf 'dump produced an empty file; nothing written\n' >&2
  exit 1
fi

printf 'wrote %s (%s)\n' "$target" "$(du -h "$target" | cut -f1)"
