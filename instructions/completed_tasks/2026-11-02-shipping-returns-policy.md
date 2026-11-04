# Completed: Shipping and Returns Policy Page

## Goal

Publish an owner-editable Wagtail page using the terms confirmed by Leah, and
make it easy to find before a shopper submits an inquiry or checks out.

## Scope

- Add a `PolicyPage` page type and seed one live Shipping & Returns page through
  an idempotent migration.
- Cover U.S. shipping, three-business-day dispatch for ready-made items, the
  agreed 30-day return terms, custom-order cancellations, damaged/wrong items,
  and the supplied support email.
- Link the page from the shop catalogue rather than global navigation.
- Add regression tests for page rendering and key policy links.

## Verification

- Apply migrations in the local Docker database.
- Run Django checks, tests, migration consistency, and a production Tailwind
  build through Docker Compose.
- Check the rendered page and links at desktop and mobile widths where browser
  tooling is available.

## Completion summary — 2026-11-02

- Added the Wagtail-editable policy page at `/shipping-returns/`, seeded as live
  content by migration `home.0014_policypage`.
- Added an internal link on the shop catalogue page and removed the policy from
  global navigation. The sitemap includes the page.
- Updated `PRODUCT.md`, the storefront plan, and backend README to reflect the
  confirmed customer terms.
- Checks: 32 Docker tests passed on a fresh test database; Django checks,
  migration checks, and Tailwind CSS build passed. Desktop and mobile renders
  were inspected; the UI detector reported no findings.
- Follow-up: Leah should review the wording against applicable local
  requirements before enabling live payments. The companion Privacy notice is
  tracked in `2026-11-02-privacy-notice.md`.
- Navigation update: the Shipping & Returns link now appears only in the shop
  catalogue, not in the header, footer, product, basket, checkout, or inquiry
  screens.
