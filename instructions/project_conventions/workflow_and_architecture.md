# Workflow and Architecture

## Default shape

- Django templates and Wagtail pages are the default; add an API or separate
  frontend only for a concrete requirement.
- Keep each feature inside its owning Django app.
- Keep views focused on request handling, validation, and responses.
- Put meaningful reusable business logic in focused service modules.
- Prefer explicit, readable solutions over clever abstractions.

## Structure as the project grows

Start with Django's normal app files. Add focused modules or packages when there
is enough related code to justify them, such as `services/`, `selectors/`,
`validators/`, or `tasks/`. Do not create empty folders automatically and avoid
catch-all modules such as `helpers.py` or `misc.py`.

## Frontend

- Use semantic HTML, accessible labels, visible focus states, and mobile-first
  layouts.
- Use Tailwind utilities for presentation and keep shared design tokens
  intentional.
- Keep content editable in Wagtail when the site owner needs to maintain it.
