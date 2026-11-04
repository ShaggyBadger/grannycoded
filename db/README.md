# Database (local development)

Three things live here, and they are not the same thing.

## `.pgdata/`

The live Postgres data directory, bind-mounted by `compose.yaml`. Postgres owns it
as uid 70 with mode 0700, so your user account cannot read it — that is normal,
not a permissions bug. Inspect it through the container:

```sh
docker compose exec db ls /var/lib/postgresql/data
```

It is gitignored and disposable: delete it and restore from a dump.

## `db/dumps/`

Custom-format `pg_dump` output. Create one with:

```sh
scripts/db-dump.sh my-label        # -> db/dumps/my-label.dump
```

Restore with:

```sh
scripts/db-restore.sh db/dumps/my-label.dump
```

Dumps are gitignored via `*.dump`.

## `.env` (in the project root)

Holds database credentials and the object-storage settings.

---

## Warnings

**This repository is public.** `.gitignore` covers `.pgdata/` and `*.dump`, but a
single `git add -f` publishes a dump containing password hashes, customer emails,
addresses, and Stripe identifiers. Never force-add anything from `db/`.

**A dump is not a backup of the site.** Product images live in the object-storage
bucket, not in the database. Restoring a dump without the bucket leaves image
records pointing at nothing. Database dump **plus** bucket contents are one unit.

**Production is authoritative after launch.** Pull production data down when you
need it; never push a development dump up except the one time you seed the site.
