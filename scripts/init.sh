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

printf '%s\n' "Loading country reference data for shipping addresses..."
docker compose run --rm --no-deps web python manage.py oscar_populate_countries --initial-only

printf '%s\n' "Starting Django and the Tailwind watcher..."
docker compose up -d tailwind web

print_admin_fallback() {
  printf '%s\n' "Could not check whether an admin user exists." \
    "Create or verify one with: docker compose exec web python manage.py createsuperuser"
}

printf '%s\n' "Checking for an existing Wagtail admin user..."
if has_superuser="$(docker compose exec -T web python manage.py shell -c \
  'from django.contrib.auth import get_user_model; print(get_user_model().objects.filter(is_superuser=True).exists())' \
  --verbosity 0 \
  | tr -d '\r\n')"; then
  case "$has_superuser" in
    True)
      printf '%s\n' "An admin user already exists; skipping creation."
      ;;
    False)
      read -r -p "Create your first Wagtail admin user now? [Y/n] " create_admin
      if [[ -z "$create_admin" || "$create_admin" =~ ^[Yy]([Ee][Ss])?$ ]]; then
        docker compose exec web python manage.py createsuperuser
      else
        print_admin_fallback
      fi
      ;;
    *)
      print_admin_fallback
      ;;
  esac
else
  print_admin_fallback
fi

printf '\n%s\n' "Site is running at http://localhost:8000/" \
  "Wagtail admin: http://localhost:8000/admin/"
