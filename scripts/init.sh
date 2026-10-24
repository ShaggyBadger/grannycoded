#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(dirname "$(dirname "$(realpath "${BASH_SOURCE[0]}")")")"
cd "$PROJECT_ROOT"

if ! command -v docker >/dev/null 2>&1; then
  printf '%s\n' "Docker is required. Install Docker Engine and the Compose plugin, then try again."
  exit 1
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  printf '%s\n' "Created .env from .env.example."
fi
chmod 600 .env

printf '%s\n' "Building the Django image..."
docker compose build web

printf '%s\n' "Configuring the site name and local secret..."
docker compose run --rm --no-deps --workdir /app --entrypoint python web scripts/configure_local_site.py

printf '%s\n' "Starting Postgres and waiting until it is ready..."
docker compose up -d --wait db

printf '%s\n' "Applying database migrations..."
docker compose run --rm --no-deps web python manage.py migrate

printf '%s\n' "Starting Django and the Tailwind watcher..."
docker compose up -d tailwind web

printf '\n%s\n' "Site is running at http://localhost:8000/" \
  "Wagtail admin: http://localhost:8000/admin/" \
  "Create your first admin user with: docker compose exec web python manage.py createsuperuser"
