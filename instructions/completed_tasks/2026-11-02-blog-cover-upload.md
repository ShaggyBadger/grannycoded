# Completed: Blog Cover Upload

## Completion summary

- Replaced the cover-asset dropdown with a styled local image upload control.
- Validated image content and supported extensions (JPG/JPEG, PNG, WebP, AVIF),
  with a 20 MB limit; leaving the field empty preserves the current cover.
- Uploads create public editorial `ImageAsset` records through the configured
  public storage backend and link them to the blog post. Linode storage is
  enabled in the current environment; replaced assets use the existing delayed
  cleanup lifecycle.
- Important files: `backend/home/wagtail_forms.py`, `backend/home/apps.py`,
  `backend/home/models.py`, `backend/static/css/wagtail-admin-branding.css`,
  and `backend/home/tests.py`.
- Verification: all 30 Docker tests, Django checks, migration consistency, and
  the Impeccable detector pass.

## Goal

Let editors upload a cover image from their computer in the Wagtail post form.
Create a validated public editorial `ImageAsset`, store it through the configured
public image backend, and link it to the post.

## Files

- `backend/home/wagtail_forms.py` for upload validation and asset creation
- `backend/home/apps.py` to attach the custom page form
- `backend/home/models.py` for the upload field panel
- `backend/static/css/wagtail-admin-branding.css` for the upload control
- `backend/home/tests.py` for upload and storage regression tests

## Steps

1. Replace the asset dropdown with an optional, validated image-upload field.
2. Save uploads as public editorial assets and preserve the current cover when
   no replacement is provided.
3. Style the input with the existing admin palette and verify admin rendering,
   asset metadata, storage, validation errors, and page linkage.

## Verification

- Run targeted/full Django tests, system checks, and migration consistency via
  Docker Compose.
- Run the Impeccable detector on the changed admin UI targets.
