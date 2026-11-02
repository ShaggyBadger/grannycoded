# Completed: Image Storage Migration

## Completion summary

- Added ULID-backed `ImageAsset` storage and links for products, the site logo,
  editorial covers, and private customer references.
- Migrated 12 product images and the logo to Linode public image storage; all 13
  anonymous object checks returned HTTP 200. A temporary private object returned
  HTTP 403 anonymously and was deleted after the check.
- Removed 13 source image binaries from `backend/static/images/`; kept provenance
  sidecars and `backend/home/catalog_image_manifest.json` for fresh-database
  imports.
- Important files: `backend/home/models.py`, `backend/home/storage.py`,
  `backend/home/management/commands/migrate_granny_images.py`,
  `backend/home/management/commands/import_granny_catalog.py`,
  `backend/home/management/commands/purge_pending_images.py`, and migration
  `0010_imageasset_blogpostpage_cover_asset_and_more.py`.
- Verification: Docker Django checks, all 20 tests, migration consistency,
  Tailwind CSS build, idempotent migration/import runs, and rendered homepage and
  five public product pages using remote image URLs.
- Follow-up repair: migration `0011_relink_legacy_product_images.py` points the
  legacy Oscar thumbnail rows at the corresponding Linode asset objects; the
  authenticated Oscar catalogue dashboard now renders successfully.
- Thumbnail repair: migration `0012_clear_product_thumbnail_cache.py` clears
  stale Easy Thumbnails records, and ULID storage preserves rendition suffixes.
  All 12 regenerated catalogue thumbnails now return anonymous HTTP 200.
- Follow-up: Leah reviews the 12 unpublished product drafts and verifies photos,
  prices, and stock before publishing.

## Goal

Move the product photos and logo from app static files to Linode Object
Storage. Keep CSS, JavaScript, fonts, and other static assets in the project.
Keep the bucket private at bucket level; grant public-read only to public site
images and keep custom-order reference photos private.

## Decisions

- Use `ImageAsset` records with ULID primary keys and preserve human-readable
  names, source paths, content hashes, visibility, and lifecycle state. Link
  public assets to products, brand settings, and editorial covers; link private
  assets to custom inquiries.
- Use a dedicated image migration command, not `collectstatic`.
- Preserve a checked-in metadata manifest so a fresh database can reconnect
  imported listings and the brand logo to already-uploaded objects without
  storing image binaries in Git.
- Keep current image binaries in Git until uploads, database references, and
  public/private access checks pass; remove them only after verification.
- When product/image relationships are deleted, queue their objects and purge
  only after checking for remaining references and waiting 30 days.

## Steps

1. Add ULID `ImageAsset` records and separate public/private storage backends.
2. Add image manifest migration for existing product photos and logo.
3. Update public templates to use managed assets and make custom inquiry image
   reads staff-only.
4. Add delayed, reference-aware asset cleanup.
5. Verify the Linode connection, migrate assets, confirm URLs and ACL behavior,
   then remove the local image binaries.

## Verification

- Run Docker Django checks, migration checks, and the full test suite.
- Test public image URLs in an anonymous browser context and confirm private
  custom-order images require staff access.
- Confirm the migration command is idempotent and cleanup previews candidates
  before deleting anything.
