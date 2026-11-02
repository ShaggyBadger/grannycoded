# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Shoppers interested in distinctive handmade goods and people drawn to vintage
quilt textiles and one-of-a-kind wearable pieces. Visitors should be able to
browse the catalog, purchase from GrannyCoded, read the maker's blog, and follow
her social channels.

## Product Purpose

GrannyCoded is the maker's own online storefront and brand home. The primary
goal is direct sales through the website; the landing page introduces the work
and leads shoppers into the store. A blog and social links support the shop and
its maker story.

## Positioning

The distinctive craft is finding quilts at thrift shops and transforming them
into one-of-a-kind clothing and accessories. The initial catalog also includes
handmade dresses, Bible bags, pouches, and fabric bookmarks.

## Operating Context

- The maker sources vintage quilts and most finished goods are one of a kind.
- Wagtail manages the public pages and editorial content. Oscar 4.2 is the
  planned source of truth for catalog, prices, stock, and orders.
- The shop owner manages editorial content in Wagtail and shop operations in
  Oscar's dashboard.
- Only finished, in-stock products are available for ordinary online purchase;
  the shop will not take preorders at launch.
- Repeatable batches share a listing and quantity. Unique pieces have their own
  listing and remain visible as sold after purchase.
- Predefined choices with distinct stock or prices are product variants. Other
  shopper-selected details are recorded with the order.
- Custom work starts as an inquiry. After the maker agrees on scope, price, and
  shipping with the customer, the full amount is invoiced before production.
- Online checkout will use Stripe-hosted Checkout first. Embedded Checkout is a
  later enhancement. Real payments remain disabled until Stripe payment
  confirmation and launch configuration are complete.
- Initial online shipping is U.S.-only, with shipping included in regular
  listing prices as a working policy. Actual costs must be checked before
  launch; custom-order shipping is quoted per order.
- In-person sales and accepted custom orders are intended to be recorded in
  Oscar. Taking products to a fair temporarily removes them from online sale;
  afterward, Leah updates stock and relists unsold pieces. Sold one-offs are
  republished with zero stock so their pages remain visible as sold.

## Capabilities and Constraints

- The existing project is Django/Wagtail with server-rendered templates and
  Tailwind CSS.
- Oscar 4.2 is the commerce framework. It has been checked with this project's
  Django 6.0.9 and Wagtail 8.0.1 versions in Docker; repeat the compatibility
  check when upgrading dependencies.
- Launch sections are Home, Shop, About/Maker story, Blog, and a custom-order
  request form. The Blog currently has an introductory post. Show social links
  only when the maker supplies their URLs.
- The saved Etsy page contains a 12-listing catalog snapshot. Listing details,
  prices, availability, and photography must be verified before publication;
  imported listings start as drafts.
- Products need finite inventory so one-of-a-kind pieces cannot be oversold.
- Guest checkout is allowed; accounts are not required. Online shipped orders
  collect contact and shipping details. In-person sales may be recorded without
  customer details unless a receipt is requested.
- Leah must verify product details, shipping economics, return policies, tax
  handling, and final editorial content before live sales.

## Brand Commitments

- Use the GrannyCoded name, supplied logo, and palette in `BRAND_COLORS.md`.
- The palette is ink `#0B0B09`, granny olive `#464E29`, moss `#68683A`, antique
  gold `#C0A070`, and warm linen `#F4EBDD`.
- Source logo: `grannycoded_logo.jpg`; Django static copy:
  `backend/static/images/grannycoded_logo.avif`.

## Evidence on Hand

- `backend/home/catalog_snapshot.json` preserves the 12-listing Etsy snapshot
  with initial price references. It is a snapshot, not a source of truth for
  current price or inventory.
- `BRAND_COLORS.md` and the supplied logo are available as brand assets.
- No verified testimonials, reviews for reuse, biography, or social URLs have
  been supplied. The published introductory blog post uses confirmed brand and
  catalog information; do not invent personal history or unsupported process
  claims in future articles.

## Product Principles

1. Make the unusual source material and transformation legible without inventing
   claims about the maker or products.
2. Treat one-of-a-kind availability as real inventory, not decorative copy.
3. Keep product price, stock, and editorial content manageable by the owner.
4. GrannyCoded owns the catalog, order flow, and customer experience; Stripe
   processes payments.
