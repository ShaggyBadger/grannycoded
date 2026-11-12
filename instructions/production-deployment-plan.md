# Production Deployment Plan

## Goal

Make the storefront runnable on the Linode host behind HTTPS, without changing
the local development workflow. The application code is already verified; this
adds the runtime that is missing.

## What exists today

`Dockerfile` and `compose.yaml` are development-only: `runserver`, a Tailwind
watcher, and a bind-mounted `.pgdata`. With `DJANGO_DEBUG=False` Django stops
serving static files, so nothing currently serves `collectstatic` output.

## Target shape

```
visitor → Caddy :443 (TLS, static/media files)
            └── everything else → gunicorn :8000 → Postgres
```

## Files

New:

- `Dockerfile.prod` — multi-stage build: Tailwind compiled in a Node stage,
  Python dependencies and gunicorn in the runtime stage, non-root user.
- `compose.prod.yaml` — `web`, `db`, `caddy`; named volumes for Postgres,
  `staticfiles`, `media`, logs, and Caddy's certificates.
- `Caddyfile` — automatic TLS, `/static/*` and `/media/*` from the shared
  volumes, everything else proxied to gunicorn.
- `scripts/docker-entrypoint.prod.sh` — refreshes collected static files, then
  hands off to the container command.
- `.env.production.example` — the production variable set with blank secrets.
- `instructions/deploy.md` — the runbook: DNS, first deploy, verify, Stripe
  cutover, updates, backups.
- `backend/home/health.py` — `/health/` returning 200 and checking the database.

Changed:

- `backend/requirements.txt` — pin `gunicorn`.
- `backend/config/urls.py` — route `/health/`.
- `backend/config/settings.py` — exempt `/health/` from the HTTPS redirect so
  the container health check works on the private network; make HSTS
  environment-driven.
- `backend/home/tests.py` — cover `/health/` and the redirect exemption.
- `README.md` — point deployment at the runbook.

Local `Dockerfile`, `compose.yaml`, and `scripts/init.sh` are untouched.

## Steps

1. Add the health endpoint, settings, and tests; run the suite.
2. Add the production image, Compose file, Caddyfile, and entrypoint.
3. Build the production image and verify `/health/`, static file serving, and a
   rendered page against a throwaway stack.
4. Write the runbook and production environment template.
5. Update progress state and the handoff note.

## Verification

- `docker compose exec web python manage.py test`
- Production image builds; `docker compose -f compose.prod.yaml config` is valid.
- A local production-mode stack serves `/`, `/shop/`, `/health/`, and
  `/static/css/site.css` with `DJANGO_DEBUG=False`.
- `manage.py check --deploy` reports no issues.

## Out of scope

The live server is unreachable from this machine (no working key for
`45.79.212.144`) and no domain is recorded, so applying this to production is a
separate step once access and DNS exist.
