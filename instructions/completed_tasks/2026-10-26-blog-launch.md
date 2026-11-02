# Completed: GrannyCoded Blog Launch

## Completion summary

- Renamed the published Wagtail index to **Blog** at `/blog/` and kept permanent redirects from `/journal/` and the former sample-post URL.
- Published and expanded **A New Life for Found Quilts** to 338 words, with an
  existing Mimi Coat product image as the cover.
- Updated the site navigation, homepage blog link, and blog page wording.
- Important files: `backend/home/context_processors.py`, `backend/templates/base.html`, `backend/home/templates/home/home_page.html`, `blog_index_page.html`, and `blog_post_page.html`.
- Verification: the Blog index and post return HTTP 200, both old URLs redirect, the cover image returns HTTP 200, and all 25 Docker tests pass.
- Follow-up: add future posts in Wagtail under **Pages → Blog**.

## Goal

Make the editorial section recognizable as a blog, publish an introductory post, and preserve the existing Journal URL with a redirect.

## Steps

1. Rename the existing Wagtail index page and visible navigation to Blog.
2. Write and publish an introductory post with an existing public product image.
3. Verify the new routes, old-path redirect, navigation visibility, and page image.

## Verification

- The Blog index and introductory post return HTTP 200.
- `/journal/` redirects to `/blog/`.
- The site navigation shows Blog after the post is published.
- The cover image URL points to an existing public image asset.
