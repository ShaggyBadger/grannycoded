# Next Session

## Where things stand

Stripe is integrated and **verified end to end in test mode**. The test purchase
exposed two bugs — paid stock was never consumed, and the cart stayed full after
payment — both fixed and covered by tests (56 passing). Commit `7a5a74a` is
pushed to `origin/main`. Local test orders were deleted and stock restored.

## Immediate next step: deploy

The app is not deployable yet. `Dockerfile` and `compose.yaml` are local-dev only
(`runserver`, Tailwind watcher, dev Postgres). Production needs:

- gunicorn (or uvicorn) pinned and used as the server command
- nginx (or Caddy) in front, with TLS
- a production Compose file and production `.env`
- `collectstatic` plus a real Tailwind build
- a `/health/` endpoint (something currently polls it and gets 404)

Server and domain exist but nothing is configured. Needed to proceed:

1. SSH host/user and OS
2. Domain name and whether DNS points at the server
3. Whether to provision over SSH or hand over files to run

Deploy with Stripe keys blank first, so checkout stays closed while the site is
publicly browsable.

## Open launch gates (block live payments, not the deploy)

- Leah verifies the 12 products: photos, prices, stock
- Shipping/returns and Privacy reviewed against real providers
- Tax handling configured
- About copy and social URLs
- GA4 Configuration tag added inside GTM container `GTM-WZG3QL5Z` (the
  container alone records no pageviews)
- `.env` has a `pk_live_…` publishable key beside a test secret key; make the
  pair consistent

See `instructions/progress_state.json` and
`instructions/completed_tasks/2026-11-10-stripe-test-verification.md`.
