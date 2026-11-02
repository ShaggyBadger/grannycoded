# Media Assets and Storage

- Product images, the brand logo, Wagtail images, and customer reference photos
  are media. CSS, JavaScript, fonts, and other application-owned files remain
  static assets in the project.
- Store uploaded images as `ImageAsset` rows with ULID primary keys, real file
  extensions, human-readable display names, source paths, content hashes, and
  visibility. `ProductImageAsset`, `BrandSettings`, and `BlogPostPage` link
  public assets to their content; custom inquiries link private assets. Never
  put customer names or email addresses in object keys.
- Keep the bucket private at bucket level. Public product, brand, and editorial
  images get public-read object ACLs; customer reference photos remain private
  and are served through a staff-authorized route.
- A storage prefix organizes objects but does not enforce access. Set object
  ACLs explicitly.
- Replacing an image creates a new ULID object. Do not overwrite the existing
  file; update its database reference instead.
- Mark unreferenced assets for deletion after their database links are removed.
  Check for remaining references and retain objects for 30 days before purging
  them from Linode. Retry failed deletes. Legacy Oscar product-image and inquiry
  image fields use a separate delayed cleanup queue; Wagtail-managed images
  follow Wagtail's lifecycle.
- Verify remote uploads and database links before removing image binaries from
  Git. Keep CSS, JavaScript, fonts, and other static assets in the repository.
- `collectstatic` does not perform image migration. Use a separate, idempotent
  management command for image uploads.
