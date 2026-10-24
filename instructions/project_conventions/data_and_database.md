# Data, Database, and Secrets

- PostgreSQL is the default database. Local development uses the Compose `db`
  service and the persistent `postgres_data` volume.
- Create and review Django migrations with model changes. Apply them in the
  intended environment only.
- Do not point ordinary local development at a production database. Use the
  local container or a development/staging database.
- Migrations transfer schema, not website content or uploaded files. At initial
  launch, an approved local database may be restored once to an empty production
  database, with its media files transferred separately. Check for test data,
  local accounts, and environment-specific settings first.
- After launch, production is authoritative. Never overwrite a live database
  with a later local development copy; publish or selectively import content.
- Do not build bidirectional database synchronization as a default workflow.
  ULIDs prevent some new-key collisions but do not merge conflicting edits,
  deletions, duplicates, or Wagtail's related page/revision trees. Wagtail's
  built-in page primary keys are integers.
- If local development needs production-like data, refresh local from a
  sanitized production snapshot; do not merge that working copy back.
- Wagtail image records refer to files stored separately by the configured
  storage backend. A content import must account for both database records and
  the referenced files. Keep development and production media storage separate.
- When several projects share a development bucket, give each project a unique
  storage `location` prefix. For production, use the site's bucket and copy the
  matching object prefix before pointing Wagtail at it.
- Keep `.env` out of Git. Commit `.env.example` with variable names and safe
  local defaults only.
- Confirm the target environment before deployment, migrations on production,
  or destructive database operations.
- Never log, paste, or commit secret keys, passwords, or tokens.
