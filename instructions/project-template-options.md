# Project Template: Pre-generated App or Scaffold Generator

## The two approaches

| Approach | Advantages | Costs |
| --- | --- | --- |
| Keep a working Django/Wagtail project in the GitHub template | Immediately inspectable and runnable; Docker, settings, Wagtail, and Tailwind are tested together; no code generator or partial-scaffold recovery to maintain. | New repos start with the same generic Python names; the template contains a real starter project. |
| Generate a project during first run | Can choose project and app package names; can initialize client-specific defaults at setup. | Becomes a maintained code generator; every generated reference, migration, rerun, and partial failure must be handled and tested. |

## Recommendation

Keep the pre-generated project for now, with generic internal names such as
`config` and `home`. Prompt for the human-facing Wagtail site name instead.
Django app names usually describe functionality, not the client. If arbitrary
Python package names become a firm requirement, build a generator from a
versioned project-template tree rather than moving or editing only `settings.py`.

The current Docker image already installs Django and Wagtail from
`backend/requirements.txt` during `docker compose build`; a generator would
scaffold inside that image rather than install those packages again.

## If a generator is chosen, template these project files

- **Project package:** `manage.py`, `settings.py`, `urls.py`, `asgi.py`,
  `wsgi.py`, and `__init__.py`. They refer to the project package and settings
  module.
- **Initial Wagtail app:** `apps.py`, `models.py`, and
  `templates/<app_name>/home_page.html`. These define the app identity and the
  starter editable homepage.
- **Shared page shell:** `templates/base.html`. It can remain a generic shared
  template asset rather than vary by client.
- **Migrations:** generate app migrations after selecting the app name and
  models; do not blindly copy existing migrations. The current migration that
  converts Wagtail's default root page refers specifically to the `home` app
  label, so it must be generated or templated if that label is configurable.

Docker/Compose, pinned requirements, Tailwind files, `.env.example`,
secret-generation utility, and setup instructions are shared infrastructure.
The setup flow should create `.env` from the example and generate its secret;
`.env` remains ignored by Git.
