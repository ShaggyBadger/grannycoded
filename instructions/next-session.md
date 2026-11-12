# Next Session

## Where things stand

The application is verified: **59 tests pass**, `manage.py check` is clean, there
are no pending migrations, and every public route returns 200 against the dev
stack. Stripe was confirmed end to end in test mode earlier.

The **production stack now exists** (commit pending): `Dockerfile.prod` (Tailwind
built at image build, gunicorn), `compose.prod.yaml` (web + db + Caddy), a
`Caddyfile` with automatic TLS, `/health/`, a production `.env` template, and the
`set_site_domain` command. It was built and run as a throwaway stack with
`DJANGO_DEBUG=False`: `/`, `/shop/`, `/health/`, `/static/css/site.css`,
`/robots.txt`, and `/sitemap.xml` all served over HTTPS, and the container health
check passed.

## Immediate next step: apply it to the server

`instructions/deploy.md` is the runbook. Two things are missing and neither can
be supplied from this machine:

1. **SSH access** to `45.79.212.144` (user `josh`) — the key offered here is
   rejected, so nothing has been touched on the server.
2. **The domain name** — `client.json` has `hosting.domains: []`. Caddy needs the
   name to resolve to the server before it can issue a certificate.

Once those exist: clone the repo, `cp .env.production.example .env`, fill it in,
`docker compose -f compose.prod.yaml up -d --build`, then migrate, populate
countries, `set_site_domain`, and create the superuser. Keep Stripe keys blank
for this deploy so the site is browsable while checkout stays closed.

## Open launch gates (block live payments, not the deploy)

- Leah verifies the 12 products: photos, prices, stock
- Shipping/returns and Privacy reviewed against real providers
- Tax handling configured
- About copy and social URLs
- GA4 Configuration tag added inside GTM container `GTM-WZG3QL5Z` (the
  container alone records no pageviews)
- `.env` has a `pk_live_…` publishable key beside a test secret key; make the
  pair consistent
- Raise `SECURE_HSTS_SECONDS` after the domain has been stable over HTTPS

See `instructions/progress_state.json` and
`instructions/completed_tasks/2026-11-10-stripe-test-verification.md`.
