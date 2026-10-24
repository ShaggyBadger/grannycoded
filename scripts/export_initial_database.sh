#!/usr/bin/env bash
set -euo pipefail
umask 077

PROJECT_ROOT="$(dirname "$(dirname "$(realpath "${BASH_SOURCE[0]}")")")"
cd "$PROJECT_ROOT"

for command_name in docker scp; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    printf 'Required command not found: %s\n' "$command_name" >&2
    exit 1
  fi
done

read -r -p "SSH destination (alias or user@host): " SSH_DESTINATION
if [[ -z "$SSH_DESTINATION" || "$SSH_DESTINATION" == *[[:space:]]* ]]; then
  printf '%s\n' "Enter one SSH alias or user@host value." >&2
  exit 1
fi

read -r -p "Remote directory [/tmp]: " REMOTE_DIRECTORY
REMOTE_DIRECTORY="${REMOTE_DIRECTORY:-/tmp}"
if [[ "$REMOTE_DIRECTORY" != /* || "$REMOTE_DIRECTORY" == *[[:space:]]* ]]; then
  printf '%s\n' "Enter an existing absolute remote directory without spaces." >&2
  exit 1
fi

printf '\n%s\n' \
  "This exports the local Compose Postgres database, including all local records." \
  "It only uploads a backup; it does not restore anything on the remote host." \
  "Check that this is the intended initial-launch content before continuing."
read -r -p "Create and upload the backup? Type 'yes' to continue: " CONFIRMATION
if [[ "$CONFIRMATION" != "yes" ]]; then
  printf '%s\n' "Cancelled."
  exit 0
fi

BACKUP_DIRECTORY="$PROJECT_ROOT/backups"
mkdir -p "$BACKUP_DIRECTORY"
chmod 700 "$BACKUP_DIRECTORY"
BACKUP_FILE="$BACKUP_DIRECTORY/initial-database-$(date -u +%Y%m%dT%H%M%SZ).dump"

printf '%s\n' "Creating the local database backup..."
docker compose exec -T db sh -c \
  'pg_dump --format=custom --no-owner --no-acl --username="$POSTGRES_USER" "$POSTGRES_DB"' \
  > "$BACKUP_FILE"
chmod 600 "$BACKUP_FILE"

if [[ ! -s "$BACKUP_FILE" ]]; then
  printf '%s\n' "The database backup is empty; refusing to upload it." >&2
  exit 1
fi

printf '%s\n' "Uploading the backup with your existing SSH configuration..."
if ! scp -p "$BACKUP_FILE" "${SSH_DESTINATION}:${REMOTE_DIRECTORY}/"; then
  printf 'Upload failed. The local backup is still at %s\n' "$BACKUP_FILE" >&2
  exit 1
fi

printf 'Backup uploaded. Local copy: %s\n' "$BACKUP_FILE"
printf '%s\n' "Restore only after confirming the target database is empty and intended for this site."
