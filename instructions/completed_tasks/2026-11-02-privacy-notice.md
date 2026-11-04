# Completed: Privacy Notice Page

## Goal

Publish a Wagtail-editable privacy notice that accurately describes the current
site's inquiry form, private reference-photo storage, necessary session
cookies, email notifications, and current checkout status.

## Scope

- Reuse the Wagtail policy-page type for a separate live Privacy page.
- Link the notice from the footer and custom-order form before personal
  information or a reference photo is submitted.
- Explain current data use, sharing with operational service providers,
  retention practice, contact options, and that online checkout is not enabled.
- Add rendering, navigation, sitemap, and form-link regression tests.

## Verification

- Apply migrations in the local Docker database.
- Run Django checks, tests, migration consistency, and Tailwind build through
  Docker Compose.
- Inspect the rendered page at desktop and mobile widths.

## Follow-up

Before deployment, review the notice against actual production hosting, storage,
and email providers, choose a retention period and deletion process for inquiry
records, and document any payment processor before checkout is enabled.

## Completion summary — 2026-11-02

- Added the live, Wagtail-editable `/privacy/` page and a footer link; the
  custom-order form links to the notice before collecting personal information.
- The notice covers the inquiry fields and private reference photos, service
  providers, optional email notifications, essential cookies, current disabled
  checkout, contact requests, and current retention behavior.
- Checks: all 33 Docker tests passed on a fresh test database; Django checks,
  migration checks, and Tailwind build passed. Privacy and custom-order pages
  were inspected at desktop and mobile sizes; the UI detector reported no
  findings.
- Follow-up: production provider details and inquiry retention/deletion policy
  still need a final decision before deployment.
