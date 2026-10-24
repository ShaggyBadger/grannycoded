# Logging and Observability

- Configure Python's standard logging centrally in `backend/config/settings.py`
  and use
  named loggers in application code.
- Write each message to rotating `debug.log`, `info.log`, `warning.log`,
  `error.log`, and `critical.log` files at its level and above.
- Rotate the first four files at 25 MB with five backups; rotate `critical.log`
  at 25 MB with one backup. Keep generated logs under `backend/logs/`, which is
  ignored by Git.
- Also send INFO-and-higher messages to the container console.
- Include useful diagnostic context, but never log credentials, tokens, or
  unnecessary personal information.
