"""Preview or perform reference-aware cleanup of Linode image objects."""

from datetime import timedelta

from django.core.files.storage import storages
from django.core.management.base import BaseCommand
from django.utils import timezone
from easy_thumbnails.models import Thumbnail
from oscar.core.loading import get_model
from wagtail.images import get_image_model
from wagtail.images.models import Rendition

from home.models import (
    BlogPostPage,
    BrandSettings,
    CustomOrderInquiry,
    ImageAsset,
    PendingImageDeletion,
    ProductImageAsset,
)


ASSET_RECOVERY_DAYS = 30
UNLINKED_ASSET_GRACE_DAYS = 30


class Command(BaseCommand):
    help = "Preview or purge image objects after their database references are removed."

    def add_arguments(self, parser):
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Update asset state and delete eligible objects; default is a dry run.",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        execute = options["execute"]
        counts = {"queued": 0, "deleted": 0, "retained": 0, "failed": 0}

        for asset in ImageAsset.objects.exclude(status=ImageAsset.Status.DELETED).iterator():
            referenced = self._asset_is_referenced(asset.pk)
            if referenced:
                if execute and asset.status == ImageAsset.Status.DELETION_PENDING:
                    asset.status = ImageAsset.Status.ACTIVE
                    asset.purge_after = None
                    asset.save(update_fields=["status", "purge_after", "updated_at"])
                counts["retained"] += 1
                continue

            if asset.status == ImageAsset.Status.ACTIVE:
                if now - asset.created_at >= timedelta(days=UNLINKED_ASSET_GRACE_DAYS):
                    counts["queued"] += 1
                    if execute:
                        asset.status = ImageAsset.Status.DELETION_PENDING
                        asset.purge_after = now + timedelta(days=ASSET_RECOVERY_DAYS)
                        asset.save(update_fields=["status", "purge_after", "updated_at"])
                continue

            if (
                asset.status == ImageAsset.Status.DELETION_PENDING
                and asset.purge_after
                and asset.purge_after <= now
            ):
                if execute:
                    self._delete_asset(asset, counts)
                else:
                    counts["queued"] += 1

        pending_files = list(
            PendingImageDeletion.objects.filter(delete_after__lte=now)
        )
        for pending in pending_files:
            if self._file_is_referenced(pending.storage_alias, pending.object_name):
                counts["retained"] += 1
                if execute:
                    pending.delete()
                continue
            if execute:
                self._delete_pending_file(pending, counts)
            else:
                counts["queued"] += 1

        prefix = "Image cleanup complete" if execute else "Image cleanup dry run"
        self.stdout.write(
            f"{prefix}: {counts['queued']} queued/due, {counts['deleted']} deleted, "
            f"{counts['retained']} retained, {counts['failed']} failed."
        )
        if not execute:
            self.stdout.write("Pass --execute to apply the cleanup.")

    @staticmethod
    def _asset_is_referenced(asset_id: str) -> bool:
        return (
            ProductImageAsset.objects.filter(asset_id=asset_id).exists()
            or BrandSettings.objects.filter(logo_asset_id=asset_id).exists()
            or BlogPostPage.objects.filter(cover_asset_id=asset_id).exists()
            or CustomOrderInquiry.objects.filter(reference_asset_id=asset_id).exists()
        )

    @staticmethod
    def _file_is_referenced(storage_alias: str, object_name: str) -> bool:
        if storage_alias == "private_images":
            return CustomOrderInquiry.objects.filter(
                reference_photo=object_name
            ).exists() or ImageAsset.objects.filter(
                private_file=object_name
            ).exclude(status=ImageAsset.Status.DELETED).exists()
        ProductImage = get_model("catalogue", "ProductImage")
        Image = get_image_model()
        return (
            ProductImage.objects.filter(original=object_name).exists()
            or Image.objects.filter(file=object_name).exists()
            or Rendition.objects.filter(file=object_name).exists()
            or Thumbnail.objects.filter(name=object_name).exists()
            or ImageAsset.objects.filter(public_file=object_name)
            .exclude(status=ImageAsset.Status.DELETED)
            .exists()
        )

    @staticmethod
    def _delete_asset(asset: ImageAsset, counts: dict) -> None:
        try:
            asset.file.storage.delete(asset.file.name)
        except Exception as exc:
            asset.purge_attempts += 1
            asset.last_purge_error = type(exc).__name__
            asset.save(
                update_fields=["purge_attempts", "last_purge_error", "updated_at"]
            )
            counts["failed"] += 1
            return

        asset.status = ImageAsset.Status.DELETED
        asset.purge_after = None
        asset.save(update_fields=["status", "purge_after", "updated_at"])
        counts["deleted"] += 1

    @staticmethod
    def _delete_pending_file(pending: PendingImageDeletion, counts: dict) -> None:
        try:
            storages[pending.storage_alias].delete(pending.object_name)
        except Exception as exc:
            pending.attempts += 1
            pending.last_error = type(exc).__name__
            pending.last_attempt_at = timezone.now()
            pending.save(
                update_fields=["attempts", "last_error", "last_attempt_at"]
            )
            counts["failed"] += 1
            return

        pending.delete()
        counts["deleted"] += 1
