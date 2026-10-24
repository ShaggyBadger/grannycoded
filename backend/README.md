# Backend

The Django/Wagtail site and the Tailwind pipeline for its server-rendered UI
live here.

- `config/` contains project settings, URL routing, and ASGI/WSGI entry points.
- Each Django app owns its models, migrations, and app-specific templates.
- Jazzmin themes Django's built-in admin at `/django-admin/`; Wagtail's admin at
  `/admin/` is separate and unchanged.
- `templates/` contains shared Django templates; `static-src/` contains Tailwind
  input, and `static/` receives generated assets.
- `requirements.txt` and the npm manifests pin the backend and Tailwind tools.

Run project commands from the repository root through Compose, for example:

```bash
docker compose exec web python manage.py check
docker compose exec web python manage.py test
docker compose exec tailwind npm run build:css
```
