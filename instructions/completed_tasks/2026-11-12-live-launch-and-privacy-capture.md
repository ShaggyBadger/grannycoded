# Completed: Live Launch Docs and Privacy Capture

## Completion summary

- Recorded the live deploy at `https://grannycoded.com` in `README.md`,
  `instructions/next-session.md`, and `instructions/progress_state.json`.
- Replaced the "add a GA4 Configuration tag" note with the published Tag Manager
  configuration: container `GTM-WZG3QL5Z` sends pageviews to GA4 property
  `G-35HS92XDW4`, with enhanced measurement on and `purchase` marked as a key
  event.
- Noted that GA4 records no ecommerce events because checkout never loads the
  container. No purchase-tracking work is planned.
- Captured the Privacy page as edited in the live Wagtail admin into
  `backend/home/migrations/0020_capture_live_privacy_notice.py`, adding one
  sentence about the analytics user-data collection that the container performs.
  The migration only rewrites bodies still carrying the pre-launch or live-launch
  copy, so a later administrator revision is preserved.
- Updated the Privacy assertions in `backend/home/tests.py` to the live wording.
- Verification: 40 tests pass, `manage.py check` is clean, and
  `makemigrations --check` reports no changes.

## Follow-up

Apply migration `home.0020` on the server with the next deploy. If the Privacy
page is edited in production before that deploy, apply the Analytics sentence by
hand instead — the migration deliberately skips a body it does not recognise.
