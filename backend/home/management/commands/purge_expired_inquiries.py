"""Preview or delete inactive custom-order inquiries past their retention period."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from home.models import CustomOrderInquiry


INQUIRY_RETENTION_DAYS = 365
ORDER_RECORD_STATUSES = (
    CustomOrderInquiry.Status.ACCEPTED,
    CustomOrderInquiry.Status.CONVERTED,
)


class Command(BaseCommand):
    help = "Preview or delete unaccepted custom inquiries inactive for 365 days."

    def add_arguments(self, parser):
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Delete eligible inquiries; default is a dry run.",
        )

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=INQUIRY_RETENTION_DAYS)
        eligible = (
            CustomOrderInquiry.objects.filter(updated_at__lt=cutoff)
            .exclude(status__in=ORDER_RECORD_STATUSES)
            .order_by("pk")
        )
        count = eligible.count()

        if options["execute"]:
            for inquiry in eligible.iterator():
                # Delete one at a time so post_delete signals queue private photos
                # for the existing delayed storage-cleanup lifecycle.
                inquiry.delete()
            self.stdout.write(f"Inquiry cleanup complete: {count} deleted.")
            return

        self.stdout.write(f"Inquiry cleanup dry run: {count} eligible for deletion.")
        self.stdout.write("Pass --execute to delete eligible inquiries.")
