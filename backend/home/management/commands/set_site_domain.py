"""Point the site records at the deployment's public domain."""

from django.conf import settings
from django.contrib.sites.models import Site as DjangoSite
from django.core.management.base import BaseCommand, CommandError
from wagtail.models import Site as WagtailSite


class Command(BaseCommand):
    help = (
        "Set the public hostname on the Wagtail site and Django's site record so "
        "generated URLs match the deployed domain."
    )

    def add_arguments(self, parser):
        parser.add_argument("hostname", help="Bare hostname, such as example.com")
        parser.add_argument(
            "--port",
            type=int,
            default=443,
            help="Site port; 443 for HTTPS deployments (default: 443)",
        )
        parser.add_argument(
            "--site-name",
            default="",
            help="Display name; defaults to the current Wagtail site name",
        )

    def handle(self, *args, **options):
        hostname = options["hostname"].strip().lower()
        if not hostname or "/" in hostname or "://" in hostname:
            raise CommandError(
                "Pass a bare hostname such as example.com, not a URL or path."
            )

        wagtail_site = (
            WagtailSite.objects.filter(is_default_site=True).first()
            or WagtailSite.objects.first()
        )
        if wagtail_site is None:
            raise CommandError("No Wagtail site exists yet; run migrate first.")

        wagtail_site.hostname = hostname
        wagtail_site.port = options["port"]
        if options["site_name"]:
            wagtail_site.site_name = options["site_name"]
        wagtail_site.save(update_fields=["hostname", "port", "site_name"])

        django_site, _ = DjangoSite.objects.get_or_create(pk=settings.SITE_ID)
        django_site.domain = hostname
        if options["site_name"]:
            django_site.name = options["site_name"]
        django_site.save(update_fields=["domain", "name"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Site records now point at {hostname}:{options['port']}."
            )
        )
