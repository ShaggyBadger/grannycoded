# Backend

The Django/Wagtail site, Oscar shop, and Tailwind pipeline for the server-rendered
UI live here.

- `config/` contains project settings, URL routing, and ASGI/WSGI entry points.
- Wagtail manages editorial pages and blog content; Oscar manages products,
  stock, baskets, and orders.
- Oscar's dashboard is at `/dashboard/`; Wagtail admin is at `/admin/`; Jazzmin
  themes Django admin at `/django-admin/`.
- Oscar's catalogue is at `/shop/` and basket at `/basket/`. Checkout uses the
  Stripe-hosted payment flow when a matching Stripe key is configured; it stays
  closed when payments are unconfigured or the key/mode disagree.
- Wagtail manages the Shipping & Returns page at `/shipping-returns/` and
  Privacy notice at `/privacy/`. The shipping policy is linked from the shop
  catalogue; Privacy is linked from the footer and custom-order form.
- Custom-order requests are saved from `/custom-order/`; staff can review them
  and record fair sales through Oscar-linked tools at `/dashboard/custom-orders/`
  and `/dashboard/record-sale/`.
- Unaccepted custom-order inquiries are retained for 12 months after their last
  activity, then eligible for deletion. Accepted and converted inquiries are
  excluded from automatic cleanup. Preview with
  `docker compose exec web python manage.py purge_expired_inquiries`; add
  `--execute` to delete eligible records. Schedule both cleanup commands
  monthly in production, running inquiry cleanup first, followed by
  `docker compose exec web python manage.py purge_pending_images --execute` to
  process due image deletions. Both commands default to dry-run behavior unless
  `--execute` is supplied.
- Each Django app owns its models, migrations, and app-specific templates.
- `templates/` contains shared Django templates; `static-src/` contains Tailwind
  input, and `static/` receives generated assets.
- `requirements.txt` and the npm manifests pin the backend and Tailwind tools.

## Search indexing

- Set `PUBLIC_SITE_URL` to the canonical production origin; canonical tags and
  `robots.txt`/`sitemap.xml` use this value.
- Set `GOOGLE_SITE_VERIFICATION` to the content value from Search Console's
  HTML-tag verification method, then submit `/sitemap.xml` in Search Console.
- `robots.txt` disallows crawling when `DEBUG=True`; production must run with
  `DEBUG=False` to allow indexing.

Run project commands from the repository root through Compose, for example:

```bash
docker compose exec web python manage.py check
docker compose exec web python manage.py test
docker compose exec tailwind npm run build:css
```
