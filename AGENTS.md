# Agent Instructions

- Start with `README.md`, then use
  `instructions/project_conventions/directory.json` to load only relevant
  guidance and app documentation.
- Keep code and reference files small, atomic, single-purpose, and nonduplicative;
  link to details rather than repeating them to conserve context and tokens.
- Keep implementation tasks small and reviewable. For non-trivial work, follow
  `instructions/project_conventions/planning_and_progress.md` and update
  `instructions/progress_state.json`.
- Use the Docker Compose commands in `README.md`; do not install project
  dependencies into the host Python environment.
- Never print or commit `.env` values. Confirm the target before production
  database, deployment, or destructive operations.
