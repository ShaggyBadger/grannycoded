# Completed: Inquiry Retention

## Completion summary

- Adopted a 365-day inactivity period for custom-order inquiries that have not
  become accepted or converted orders. Accepted and converted inquiries are
  excluded from automated cleanup.
- Added dry-run-first `purge_expired_inquiries`; `--execute` deletes eligible
  records individually so the existing private-photo deletion lifecycle runs.
- Updated the live Privacy page using a guarded data migration that only
  replaces the original default text, preserving administrator-edited notices.
- Documented monthly inquiry cleanup followed by due-image cleanup.
- Verification: all 35 Docker tests pass; Django system checks and
  `makemigrations --check` pass.

## Operations

Preview and execute commands:

```bash
docker compose exec web python manage.py purge_expired_inquiries
docker compose exec web python manage.py purge_expired_inquiries --execute
docker compose exec web python manage.py purge_pending_images
docker compose exec web python manage.py purge_pending_images --execute
```

Schedule the execute commands monthly in production, running inquiry cleanup
before pending-image cleanup. Keep accepted/converted order records according
to applicable business and record-keeping requirements.
