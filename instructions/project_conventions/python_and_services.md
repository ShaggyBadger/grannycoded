# Python and Services

- Use descriptive names and explicit control flow.
- Add type hints where they clarify interfaces or non-obvious data.
- Keep functions focused; move business logic out of views when it becomes
  meaningful, multi-step, reusable, or independently testable.
- Use a package such as `services/` when an app's related service code grows
  beyond a small focused module. Do not create packages just to anticipate
  hypothetical complexity.
- Raise useful errors and catch exceptions only when adding recovery or useful
  context. Never silently hide failures.
- Read configuration from environment variables; do not hardcode credentials.
