# GrannyCoded Storefront Plan

## Goal

Build GrannyCoded's direct-sales website with Oscar-owned commerce and Wagtail
editorial content. Product purpose and verified brand facts are in
[`PRODUCT.md`](../PRODUCT.md).

## Agreed requirements

- **Ownership:** Oscar is the source of truth for products, prices, stock, and
  orders. Wagtail owns Home, About/Maker story, Blog, and the custom-order
  request form. Leah uses the Oscar dashboard for shop operations and Wagtail
  for editorial updates.
- **Catalog:** Import the 12 saved Etsy listings as drafts. Leah verifies each
  product's description, price, photos, and actual stock before publishing.
  Sell finished stock only; do not offer preorders at launch.
- **Inventory:** A batch of similar items uses one listing with its available
  quantity. A genuinely unique piece has its own listing, remains visible as
  sold, and has no available stock. Use variants when a predefined choice has
  its own price or stock count; record other choices on the order.
- **Checkout:** Guest checkout is allowed; customers do not need an account.
  Online shipped orders collect email and shipping address. Blog and About
  content must use real maker-supplied material; omit unavailable social links.
- **Custom work:** A short request form starts the process. Leah reviews the
  request, agrees on details, price, and shipping, then records an accepted
  custom order in Oscar. The full agreed amount is invoiced before production.
- **In-person sales:** Record fair sales in Oscar, including anonymous walk-up
  sales when no receipt is requested. Hide listings before taking items to a
  fair; afterward update the remaining quantity, relist unsold stock, and
  republish sold one-offs with zero stock so their pages remain visible as sold.
- **Shipping:** Launch online shipping is U.S.-only. Regular listing prices
  include shipping as a working policy; validate actual costs before launch.
  Custom-order shipping is decided and disclosed per quote.
- **Returns and tax:** Verify Leah's current Etsy return policy for standard
  items and decide a separate policy for custom work. Confirm tax handling and
  configure it before enabling live payments.
- **Payments:** Build and test the storefront with payments disabled. In a later
  payment phase, integrate Stripe-hosted Checkout for catalog orders and
  Oscar-linked Stripe invoices for accepted custom orders. Add verified,
  idempotent webhook processing before any live payment. Embedded Checkout is
  a later UI enhancement; it does not replace webhook confirmation.

The Oscar/Wagtail boundary is recorded in
[`docs/adr/0001-oscar-for-commerce-wagtail-for-content.md`](../docs/adr/0001-oscar-for-commerce-wagtail-for-content.md).
Image identifiers, object access, and deletion lifecycle are recorded in
[`docs/adr/0002-ulid-image-assets-and-lifecycle.md`](../docs/adr/0002-ulid-image-assets-and-lifecycle.md).

## Phases

1. **Complete — compatibility and architecture:** Oscar 4.2 passes Docker system checks
   and tests with the project's pinned Django 6.0.9 and Wagtail 8.0.1. Keep
   Oscar authoritative for commerce and Wagtail authoritative for editorial
   content; re-run the check on dependency upgrades.
2. **Built — storefront and catalog:** public pages and Oscar catalog workflows
   are in place. The 12 existing Wagtail listings were transferred to Oscar as
   unpublished drafts with zero stock; batches, one-off pieces, and
   stock-bearing variants are supported.
3. **Built — offline and custom-order workflows:** Oscar-linked staff tools
   record in-person sales and turn accepted custom quotes into pending Oscar
   orders. Stripe invoices are intentionally deferred to the payment phase.
4. **Deferred — payment integration:** after the storefront and product data are
   ready, add Stripe-hosted
   Checkout, invoice integration, and verified/idempotent webhook processing.
   Keep live payments disabled through implementation and test-mode validation.
5. **Pending — launch readiness and later improvements:** verify product data, shipping
   economics, tax setup, policies, and domain before enabling live payments.
   Consider embedded Checkout only after the hosted flow is working.

## Open decisions and gates

- Leah must verify the saved 12-product snapshot and provide current prices,
  availability, and photos before publication.
- Confirm free-shipping economics using labor, packaging, postage, and payment
  fees, not material cost alone.
- Confirm tax configuration and the custom-order return/cancellation policy
  before enabling live payments. Confirm the existing standard-item policy
  before publishing it.
- Configure a notification recipient and mail transport if Leah wants automatic
  emails for new custom-order requests; each request is saved for staff review.
- Obtain real About copy, blog posts, and social URLs; do not invent them.
- Oscar's standard order dashboard does not provide a manual order-creation
  route. The fair-sale and custom-order entry workflows require custom admin
  work; see the cited Oscar 4.2 routes in the ADR.
- Before enabling checkout, reject a product that Leah delisted after it was
  added to an existing basket. Oscar 4.2's default checkout validation checks
  availability, so the payment-phase integration must also test current
  publication/withdrawal state ([Oscar checkout source](https://github.com/django-oscar/django-oscar/blob/4.2/src/oscar/apps/checkout/session.py)).

## Verification

- Run `docker compose exec web python manage.py check` and
  `docker compose exec web python manage.py test`; verify migrations locally.
- Test Oscar/Wagtail compatibility, variant stock, batch quantity, sold-page
  behavior, fair withdrawal/relisting, and custom/offline order recording.
- In the Stripe phase, test concurrent one-off checkout, a fair withdrawal while
  an item is in a basket, invoice payment updates, webhook signature/idempotency,
  failure/expiry, and inventory release.
- Build Tailwind and inspect Home, Shop, sold/out-of-stock, and request-form
  states at mobile and desktop sizes, including keyboard access and focus.
