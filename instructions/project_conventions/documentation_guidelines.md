# Documentation Guidelines

- Keep `AGENTS.md` short and limited to rules that apply to nearly every task;
  route detailed guidance through `directory.json`.
- Before adding guidance, check the router and related documents. Update the
  existing source of truth instead of creating duplicate rules.
- Keep each instruction file focused on one topic, concise, and actionable.
  Prefer a short link over repeating commands, examples, or background.
- When adding, renaming, or removing a topic, update `directory.json` with a
  useful summary and clear `when_to_read` triggers.
- Put reusable conventions in the template repository. Keep client-specific requirements and
  decisions in that client's repository; promote only generally useful lessons
  back to the template.
- Keep session handoffs and progress state temporary. Remove stale guidance
  rather than preserving it "just in case."
- Before publishing the reusable template, reset working state and remove
  client-irrelevant Outpost handoff or completed-work history.
