#!/usr/bin/env bash
# Restore a dump into the local development database.
set -euo pipefail

PROJECT_ROOT="$(dirname "$(dirname "$(realpath "${BASH_SOURCE[0]}")")")"
cd "$PROJECT_ROOT"

if [[ $# -lt 1 ]]; then
  printf 'usage: scripts/db-restore.sh path/to/file.dump\n' >&2
  exit 1
fi

dump="$1"
[[ -f "$dump" ]] || { printf 'no such file: %s\n' "$dump" >&2; exit 1; }

docker compose up -d --wait db

docker compose exec -T db sh -lc \
  'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner' < "$dump"

printf 'restored %s\n' "$dump"
printf 'start the app with: docker compose up -d\n'
