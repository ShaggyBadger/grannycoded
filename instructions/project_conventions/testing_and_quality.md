# Testing and Quality

- Add a regression test for a bug fix when practical.
- Test new behavior at the layer that owns it; keep domain logic testable
  without a browser where possible.
- Run relevant checks inside Docker:

  ```bash
  docker compose exec web python manage.py check
  docker compose exec web python manage.py test
  ```

- For frontend work, verify narrow and wide layouts, keyboard use, visible
  focus, and empty/error states as relevant.
