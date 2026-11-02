# Completed: Technical SEO Baseline

## Completion summary

- Replaced the Wagtail starter text with a branded homepage title and added page descriptions, canonical URLs, Open Graph tags, Twitter card metadata, and Organization/WebSite JSON-LD.
- Added `robots.txt` and `sitemap.xml` for live public Wagtail pages, Oscar products/categories, the shop, and custom-order page. Local debug sites disallow crawling; cart, checkout, account, dashboard, and search pages receive noindex metadata.
- Added optional `GOOGLE_SITE_VERIFICATION` HTML-tag content configuration.
- Important files: `backend/home/seo.py`, `backend/config/urls.py`, `backend/config/settings.py`, `backend/templates/base.html`, public page templates, `backend/README.md`, and `backend/home/tests.py`.
- Verification: all 23 Docker tests, Django system checks, and migration consistency checks passed.
- Follow-up: set `PUBLIC_SITE_URL` to the production domain, add the Search Console verification content, and submit `/sitemap.xml` in Google Search Console.

## Goal

Replace the Wagtail starter title and provide crawl-ready metadata for GrannyCoded's public pages, shop, and editorial content.

## Files

- `backend/templates/base.html` and public page templates
- `backend/home/seo.py`, `backend/config/urls.py`, and `backend/config/settings.py`
- `.env.example` and `backend/home/tests.py`

## Steps

1. Use useful page titles/descriptions and canonical/Open Graph metadata, with the configured public domain.
2. Add sitemap and robots endpoints covering public Wagtail pages, products, and categories while excluding private and non-indexable routes.
3. Add optional Google Search Console meta-tag verification from configuration.
4. Test SEO metadata, sitemap contents, robots policy, and the existing storefront.

## Verification

- Docker Django checks and tests pass.
- Homepage HTML contains the branded title, canonical URL, description, and optional verification tag.
- Sitemap includes live public content and excludes drafts; robots policy is production-safe and blocks indexing on local debug sites.
