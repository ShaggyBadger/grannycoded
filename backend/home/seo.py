"""Search-engine metadata and public crawl endpoints."""

from datetime import date, datetime
from urllib.parse import urlencode, urlsplit
from xml.etree import ElementTree

from django.conf import settings
from django.http import HttpResponse
from oscar.core.loading import get_model
from wagtail.models import Page, Site


SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
ElementTree.register_namespace("", SITEMAP_NAMESPACE)


def seo_metadata(request):
    """Provide a configured canonical URL and indexing policy to templates."""
    path = request.path or "/"
    canonical_url = f"{settings.PUBLIC_SITE_URL}{path}"
    page_number = request.GET.get("page", "")
    if page_number.isdecimal() and int(page_number) > 1 and not request.GET.get("q"):
        canonical_url = f"{canonical_url}?{urlencode({'page': int(page_number)})}"

    noindex_prefixes = (
        "/admin/",
        "/django-admin/",
        "/dashboard/",
        "/basket/",
        "/checkout/",
        "/accounts/",
    )
    should_noindex = (
        settings.DEBUG
        or request.path.startswith(noindex_prefixes)
        or bool(request.GET.get("q"))
    )
    return {
        "canonical_url": canonical_url,
        "public_site_url": settings.PUBLIC_SITE_URL,
        "google_site_verification": settings.GOOGLE_SITE_VERIFICATION,
        "seo_should_noindex": should_noindex,
    }


def sitemap_xml(request):
    """List the shop, live public pages/products, categories, and custom orders."""
    locations = {}
    for path in ("/shop/", "/custom-order/"):
        locations[_absolute_url(path)] = None

    site = Site.find_for_request(request) or Site.objects.filter(is_default_site=True).first()
    if site:
        pages = Page.objects.live().public().filter(
            path__startswith=site.root_page.path
        ).specific()
        for page in pages:
            relative_url = page.get_url(request=request, current_site=site)
            if relative_url:
                last_modified = page.last_published_at
                locations[_absolute_url(relative_url)] = last_modified

    Product = get_model("catalogue", "Product")
    for product in (
        Product.objects.browsable()
        .exclude(structure=Product.CHILD)
        .only("id", "slug", "date_updated")
    ):
        locations[_absolute_url(product.get_absolute_url())] = product.date_updated

    Category = get_model("catalogue", "Category")
    shop_root = Category.get_root_nodes().filter(slug="shop").first()
    if shop_root:
        for category in shop_root.get_descendants().browsable():
            locations[_absolute_url(category.get_absolute_url())] = None

    urlset = ElementTree.Element(f"{{{SITEMAP_NAMESPACE}}}urlset")
    for location, last_modified in sorted(locations.items()):
        url_element = ElementTree.SubElement(
            urlset, f"{{{SITEMAP_NAMESPACE}}}url"
        )
        ElementTree.SubElement(
            url_element, f"{{{SITEMAP_NAMESPACE}}}loc"
        ).text = location
        if last_modified:
            ElementTree.SubElement(
                url_element, f"{{{SITEMAP_NAMESPACE}}}lastmod"
            ).text = _date_string(last_modified)

    content = ElementTree.tostring(
        urlset,
        encoding="utf-8",
        xml_declaration=True,
    )
    return HttpResponse(content, content_type="application/xml; charset=utf-8")


def robots_txt(request):
    """Prevent indexing local environments and keep staff paths out of crawls."""
    lines = ["User-agent: *"]
    if settings.DEBUG:
        lines.append("Disallow: /")
    else:
        lines.extend(
            [
                "Allow: /",
                "Disallow: /admin/",
                "Disallow: /django-admin/",
                "Disallow: /dashboard/",
            ]
        )
        lines.append(f"Sitemap: {settings.PUBLIC_SITE_URL}/sitemap.xml")
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


def _absolute_url(url: str) -> str:
    parsed = urlsplit(url)
    path = parsed.path or "/"
    return f"{settings.PUBLIC_SITE_URL}{path}"


def _date_string(value: date | datetime) -> str:
    return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
