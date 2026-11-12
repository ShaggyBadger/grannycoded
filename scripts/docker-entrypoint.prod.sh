#!/bin/sh
# Production container entrypoint.
#
# Caddy serves collected static files from a shared volume, so refresh them on
# every start. Without --clear, removed files linger but a running site never
# loses its stylesheet mid-deploy.
set -eu

python manage.py collectstatic --noinput >/dev/null

exec "$@"
