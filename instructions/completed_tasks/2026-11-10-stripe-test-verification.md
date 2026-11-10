# Completed: Stripe Test-Mode Verification

## Completion summary

- Ran a real Stripe-hosted Checkout payment end to end against local Docker and
  the Stripe CLI: a $12 bookmark paid with `4242 4242 4242 4242`, redirected to
  `/checkout/complete/`, and produced order 100027.
- Confirmed the signed webhook is delivered once, returns `200`, records
  `StripeEvent`, and creates one Oscar order with the right total, line, email,
  and U.S. shipping address.
- Confirmed negative paths: replaying the same event logs `duplicate` and creates
  no second order; a bad signature returns `400` and stores no event.
- Fixed two launch-blocking defects the payment exposed:
  - Stock allocation was never consumed, so `num_in_stock` stayed unchanged after
    a paid order. `_fulfil` now calls `consume_stock_allocations`, taking the
    bookmark from 12 to 11 and clearing `num_allocated`.
  - The shopper's basket stayed open after payment, so the confirmation page still
    showed `Cart (1)` and the paid items could be re-checked out. `CheckoutSession`
    now stores `basket_id`, and fulfilment marks that basket `submitted`.
- Also release the stock reservation and mark the session `failed` when Stripe
  refuses to create a session, instead of holding stock for the full expiry.
- Tests: added `basket_id` coverage, a basket-closing test, and corrected the
  stock assertion; all 56 Docker tests pass plus Django checks and migrations.

## Notes

- The previous local verification left a paid test order in the dev database; it
  was deleted and the bookmark's stock restored to 12. Do not export local
  payment-test data to production.
- `STRIPE_WEBHOOK_SECRET` in `.env` was replaced with the current `stripe listen`
  secret. It is local-only and becomes stale when the CLI session ends.
- `.env` still pairs a live publishable key (`pk_live_…`) with a test secret key.
  Hosted Checkout does not use the publishable key, but the pair should be made
  consistent before launch.
