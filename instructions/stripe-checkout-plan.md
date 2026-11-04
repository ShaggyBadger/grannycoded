# Stripe Checkout Plan

## Goal

Let customers pay for shop orders on the live site using Stripe-hosted Checkout,
with GrannyCoded keeping ownership of catalog, stock, and order records.

Decisions already made:

- **Hosted Checkout, not embedded.** The shopper leaves for Stripe's page, pays,
  and returns. Stripe's own domain is the reassurance; no custom domain
  subscription ($10/month) at launch.
- **The card never reaches our server.** We store a session reference and the
  Stripe webhook result, never card data. This keeps PCI scope at SAQ A.
- **Test mode until launch gates clear.** Real keys require explicit
  configuration and a separate launch step.

## User-facing flow

1. Basket summary shows an order summary and a "Continue to secure payment"
   action instead of the disabled-checkout placeholder.
2. A **Payment & security** page (linked from the footer and the basket) states
   in plain language that Stripe processes the payment and GrannyCoded never
   sees or stores card details. It carries Stripe's wordmark and card marks.
3. The action creates a Stripe Checkout Session and redirects to it. Stripe
   collects email, U.S. shipping address, and payment, and offers Apple Pay and
   Google Pay.
4. Success returns to `/checkout/complete/`; cancellation returns to the basket
   with the cart intact.
5. The webhook confirms payment and creates the Oscar order.

## Why the pre-payment page exists

Trust is lost before the payment step. Baymard's 2025 survey puts "didn't trust
the site with my credit card" at 19% of non-browsing abandonments. The page
carries the total cost, the Stripe statement, policy links, and wallet
availability, so the shopper decides before the domain changes.

## Data model

New models in `home`:

- `CheckoutSession` — ULID primary key, Stripe session id, contact email,
  shipping address snapshot, line-item snapshot (product, quantity, unit price),
  status (`pending`, `paid`, `expired`, `cancelled`), resulting Oscar order
  number, timestamps.
- `StockReservation` — product, quantity, `expires_at`, link to the checkout
  session. Available stock is `num_in_stock` minus active reservations.
- `StripeEvent` — unique Stripe event id, type, `processed_at`. The webhook
  inserts before processing so a retried event is a no-op.

Snapshots matter: prices and product names must not change under a paid order.

## Implementation steps

1. **Settings and dependency.** Add pinned `stripe` to `requirements.txt`.
   Read `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, and
   `STRIPE_PUBLISHABLE_KEY` from the environment. Add `STRIPE_ENABLED`
   (derived: keys present) and `STRIPE_LIVE_MODE` (default false). Extend
   `.env.example`.
2. **Models and migration.** The three models above, with an index on
   reservation expiry.
3. **Stock service.** `home/services/stock_reservation.py`: reserve, release,
   expire, and `available_quantity(product)`. Everything atomic and
   row-locked so two shoppers cannot reserve the same one-off.
4. **Session creation view.** `POST /checkout/` — reject withdrawn or
   unpublished products, reject quantities above available stock, reserve
   stock, snapshot the basket, create the Stripe session with
   `client_reference_id` set to our `CheckoutSession.id`, 30-minute expiry, and
   `shipping_address_collection` limited to `US`. Redirect to Stripe.
5. **Webhook.** `POST /checkout/webhook/` — CSRF-exempt, signature verified,
   idempotent. Handles `checkout.session.completed` (create the Oscar order via
   the existing `oscar_orders.create_oscar_order` service, convert the
   reservation to a sale) and `checkout.session.expired` (release stock).
6. **Return pages.** `/checkout/complete/` reads the session by id, confirms
   payment, and shows the order number. Never trusts the query string alone;
   the page re-checks our own record.
7. **Templates.** Payment summary page, confirmation page, and the Payment &
   security page, all in the existing Tailwind style.
8. **Copy.** Plain-language Stripe statement, no invented security claims.

## Verification

- Unit tests for reservation contention (two concurrent reserves of one item),
  expiry release, price snapshotting, webhook idempotency, a replayed event,
  a signature failure, and a delisted product rejected at session creation.
- Stripe CLI `stripe listen --forward-to localhost:8000/checkout/webhook/`
  against test mode, paying with `4242 4242 4242 4242`.
- Confirm the order appears in the Oscar dashboard with the right total and
  stock decremented once.
- Confirm Apple Pay/Google Pay appear on the Stripe page in a supported browser.

## Launch gates (unchanged by this work)

Live keys stay off until Leah verifies product data, shipping economics are
checked, tax handling is configured, and the policy pages are reviewed.

## Deployment

Tracked separately in the deployment plan; the webhook needs a public HTTPS
URL, so deployment precedes live-key testing.
