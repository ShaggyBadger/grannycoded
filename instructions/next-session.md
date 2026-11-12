# Next Session

## Where things stand

The store is **live at `https://grannycoded.com`** on the Linode server: gunicorn,
Postgres, and Caddy with TLS, all three containers healthy, `www` redirecting to
the bare domain. Checkout is closed until Stripe live keys and the live webhook
destination are added. Content is now authored in the production Wagtail admin;
production is the source of truth.

Verified after launch: `/`, `/shop/`, product pages, `/blog/`, `/custom-order/`,
`/privacy/`, `/shipping-returns/`, and `/sitemap.xml` all serve `https://` URLs.
The GTM container `GTM-WZG3QL5Z` is on the public pages and sends pageviews to
GA4 property `G-35HS92XDW4`.

The Privacy page was edited in the live admin during launch and drifted from the
repository; `backend/home/migrations/0020_capture_live_privacy_notice.py` now
records that copy and adds the Analytics user-data disclosure.

## Open launch gates (block live payments, not the deploy)

- Leah verifies the products: photos, prices, stock
- Tax handling configured
- `.env` has a `pk_live_…` publishable key beside a test secret key; make the
  pair consistent
- Live webhook destination created for
  `https://grannycoded.com/checkout/webhook/`
- Raise `SECURE_HSTS_SECONDS` after the domain has been stable over HTTPS
- Submit `/sitemap.xml` in Google Search Console, and confirm the GA4 tag in
  GA4 → Realtime

## Known gap

GA4 cannot record purchases: the container is suppressed on `/basket/`,
`/checkout/`, and `/accounts/`, so no ecommerce events exist. This is documented
in `README.md` (Analytics) and is deliberately unplanned.

See `instructions/progress_state.json` and
`instructions/completed_tasks/2026-11-10-stripe-test-verification.md`.
