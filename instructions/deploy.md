# Deploying GrannyCoded

Production runs three containers on the Linode host: `caddy` terminates TLS and
serves static/media files, `web` runs gunicorn, and `db` runs Postgres. Local
development still uses `compose.yaml`; nothing here changes that.

## What Caddy needs from you

Caddy obtains and renews Let's Encrypt certificates by itself, but it is not
psychic. Before the first deploy:

1. **A domain name:** `grannycoded.com`.
2. **Two DNS records** at Porkbun, both pointing at the server:

   | Type | Host | Answer | TTL |
   |---|---|---|---|
   | A | *(blank — apex)* | the server IP | 600 |
   | A | `www` | the server IP | 600 |

   Delete any parking answers on those two names first, and leave `MX` and the
   SPF `TXT` record alone. Verify with `dig +short grannycoded.com` and
   `dig +short www.grannycoded.com`; both must return the server IP before Caddy
   can pass the certificate challenge.
3. **Ports 80 and 443 open** on the host (`ufw`) and at any Linode Cloud
   Firewall. Port 80 is needed for the certificate challenge and the redirect.
4. **Optional: an email address** for certificate-expiry notices. Add
   `email you@example.com` in the global block at the top of `Caddyfile`.

Nothing else is manual: certificate storage lives in the `caddy_data` volume and
survives restarts. `SITE_DOMAIN` in `.env` is the only place the hostname is
written. Caddy serves both names; `www` answers with a permanent redirect to the
bare domain, preserving the path and query string.

## First deploy

```bash
ssh josh@<server>
git clone git@github.com:ShaggyBadger/grannycoded.git /srv/grannycoded
cd /srv/grannycoded
cp .env.production.example .env
chmod 600 .env
$EDITOR .env          # fill in every blank; see the comments in the file
```

Generate the two secrets it asks for:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"   # DJANGO_SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"   # POSTGRES_PASSWORD
```

Leave the Stripe keys **blank** for the first deploy. Checkout then stays
closed while the site is publicly browsable.

Start the stack and prepare the database:

```bash
docker compose -f compose.prod.yaml up -d --build
docker compose -f compose.prod.yaml run --rm web python manage.py migrate
docker compose -f compose.prod.yaml run --rm web python manage.py oscar_populate_countries --initial-only
docker compose -f compose.prod.yaml run --rm web python manage.py set_site_domain "$(grep ^SITE_DOMAIN= .env | cut -d= -f2)" --site-name GrannyCoded
docker compose -f compose.prod.yaml run --rm web python manage.py createsuperuser
```

`set_site_domain` matters: the database template ships pointing at localhost,
which would leave Wagtail's generated links and the Django site record on the
wrong host.

## Choosing the initial content

Pick one, from `README.md` ("Moving real content to a live site"):

- **Enter it in the live admin.** Simplest and safest. No dump, no media copy.
- **Restore an approved local database.** Only while production is still empty.
  Dump locally, copy the file up, restore into `db`, then copy the referenced
  media. Check for test orders, local accounts, and local site settings first.
- **Production already has content.** Do not restore over it. Import pages
  selectively or recreate them.

## Verify the deploy

```bash
curl -sI https://<domain>/health/          # 200, {"status": "ok"}
curl -sI https://www.<domain>/             # 301 to https://<domain>/
curl -s  https://<domain>/sitemap.xml | head -20   # https:// URLs, not localhost
docker compose -f compose.prod.yaml ps     # all three healthy
docker compose -f compose.prod.yaml logs -f web
```

`<domain>` in `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, and
`PUBLIC_SITE_URL` must match the canonical bare domain; `www` only redirects, so
it is listed in the host and CSRF settings for safety but never proxies to
Django.

Then in a browser: `/`, `/shop/`, a product page, `/blog/`, `/custom-order/`,
`/privacy/`, `/shipping-returns/`, and `/admin/` with the superuser.

If the certificate fails, `docker compose -f compose.prod.yaml logs caddy`
usually names the reason: DNS not resolving here yet, or port 80 blocked.

## Switching payments on

Follow "Going live" in `README.md`. The parts specific to this stack:

```bash
docker compose -f compose.prod.yaml exec web python -c "
import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings');django.setup()
from django.conf import settings as s
print('mode:', 'LIVE' if s.STRIPE_KEY_IS_LIVE else 'test', '| checkout:', s.STRIPE_ENABLED)"
```

The webhook endpoint is `https://<domain>/checkout/webhook/`. After changing
`.env`, recreate the container so the new values load:

```bash
docker compose -f compose.prod.yaml up -d web
```

## Operating it

```bash
docker compose -f compose.prod.yaml logs -f web         # gunicorn + app logs
docker compose -f compose.prod.yaml restart web
docker compose -f compose.prod.yaml ps
docker stats --no-stream
```

Logs also rotate on disk inside the `logs` volume; `docker compose exec web
ls /app/backend/logs` shows them.

### Deploying a change

```bash
cd /srv/grannycoded
git pull
docker compose -f compose.prod.yaml build web
docker compose -f compose.prod.yaml run --rm web python manage.py migrate
docker compose -f compose.prod.yaml up -d
```

Applying migrations before the new containers start keeps the schema ahead of
the code, which is the order that tolerates a slow restart.

### Backup

```bash
docker compose -f compose.prod.yaml exec -T db pg_dump -U website website | gzip > ~/backup-$(date +%F).sql.gz
```

Media lives in Linode Object Storage when `USE_LINODE_OBJECT_STORAGE=True`;
a database dump does not include it. Storage has its own retention, so schedule
a bucket copy only if that policy is not enough.

## Notes and known warnings

- `manage.py check --deploy` reports the HSTS warnings (W004/W005/W021) until
  `SECURE_HSTS_SECONDS` is raised and, if wanted, subdomains and preload are
  enabled. Start at `3600` while the domain settles, then `31536000`.
- Django redirects everything to HTTPS except `/health/`, which the container
  health check calls over plain HTTP on the private network. Caddy is the only
  route in; `web` publishes no host port.
- The Tailwind stylesheet is built into the image, and `collectstatic` runs at
  every container start into the shared `staticfiles` volume. A stale CSS
  problem therefore means a stale image, not a stale volume.
- `www` redirects to the bare domain. There is no wildcard: an unknown
  subdomain does not resolve, which keeps certificate handling to the two names
  the site actually uses.
