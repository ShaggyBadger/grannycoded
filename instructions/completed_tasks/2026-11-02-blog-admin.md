# Completed: Blog Admin Workflow

## Completion summary

- Added a Wagtail sidebar shortcut that opens the Blog's child-page list, with
  the existing post editor and add-post action available from there.
- Clarified the post title, short summary, body, and cover-image fields, and
  removed the duplicate legacy cover-image control from the editor.
- Page 4 is the Blog index; the pre-filled post is a separate child page.
- Important files: `backend/home/wagtail_hooks.py`,
  `backend/home/models.py`, and `backend/home/tests.py`.
- Verification: all 28 Docker tests, Django system checks, migration
  consistency, and the UI detector pass.

## Goal

Make the Wagtail blog post list, create action, and existing post editor obvious
to the site owner without replacing Wagtail's page workflow.

## Files

- `backend/home/wagtail_hooks.py` for a direct Blog posts admin-menu link
- `backend/home/models.py` for clearer BlogPostPage editor panels
- `backend/home/tests.py` for menu and editor regression coverage

## Steps

1. Link the admin sidebar directly to the Blog index's child-page explorer.
2. Clarify the post title, excerpt, body, and cover-image fields.
3. Test the link visibility/target and ensure the post fields remain editable.

## Verification

- Run targeted Django tests and `manage.py check` through Docker Compose.
- Confirm page 4 is the Blog index and its child post opens its own editor.
