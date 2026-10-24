# Planning and Progress

## Keep work manageable

- Break work into small, reviewable tasks with clear outcomes.
- Clarify materially ambiguous behavior before planning implementation.
- Write a plan under `instructions/` for a new feature, database change,
  architectural decision, or work spanning several files.
- A plan should state the goal, relevant files, implementation steps, and
  verification. Keep it short enough to use while working.
- For a trivial one-file fix with an obvious outcome, a plan is unnecessary.

## Progress and archives

- `instructions/progress_state.json` is the compact resume point for active
  non-trivial work.
- Update it when work starts, changes phase, pauses, or completes.
- Keep active plans in `instructions/` and move finished plans to
  `instructions/completed_tasks/` with a date in the filename.
- Add a short completion summary to archived plans: what changed, key files,
  checks run, and any follow-up.
