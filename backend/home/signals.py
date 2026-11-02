"""Queue image objects for delayed cleanup after their database rows are deleted."""

from datetime import timedelta
from pathlib import PurePosixPath

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from oscar.core.loading import get_model

from home.asset_ids import ULID_PATTERN, new_ulid
from home.models import (
    BlogPostPage,
    BrandSettings,
    CustomOrderInquiry,
    ImageAsset,
    PendingImageDeletion,
    ProductImageAsset,
)


ASSET_RECOVERY_DAYS = 30


def queue_image_deletion(storage_alias: str, object_name: str) -> None:
    if not object_name:
        return
    PendingImageDeletion.objects.get_or_create(
        storage_alias=storage_alias,
        object_name=object_name,
        defaults={"delete_after": timezone.now() + timedelta(days=ASSET_RECOVERY_DAYS)},
    )


@receiver(post_delete, sender=get_model("catalogue", "ProductImage"))
def queue_product_image_delete(sender, instance, **kwargs):
    queue_image_deletion("default", instance.original.name)


@receiver(pre_save, sender=get_model("catalogue", "ProductImage"))
def assign_product_image_ulid(sender, instance, **kwargs):
    image_file = instance.original
    if not image_file or image_file._committed:
        return

    image_id = instance.code or ""
    if not ULID_PATTERN.fullmatch(image_id):
        image_id = new_ulid()
    instance.code = image_id
    instance.original.name = f"{image_id}{PurePosixPath(image_file.name).suffix.lower()}"


@receiver(post_delete, sender=CustomOrderInquiry)
def queue_custom_reference_delete(sender, instance, **kwargs):
    queue_image_deletion("private_images", instance.reference_photo.name)
    _schedule_asset_retirement(instance.reference_asset_id)


@receiver(post_delete, sender=ProductImageAsset)
def retire_unlinked_product_image(sender, instance, **kwargs):
    _schedule_asset_retirement(instance.asset_id)


@receiver(post_save, sender=ProductImageAsset)
def restore_linked_product_image(sender, instance, **kwargs):
    _restore_asset(instance.asset_id)


@receiver(post_delete, sender=BlogPostPage)
def retire_unlinked_blog_cover(sender, instance, **kwargs):
    _schedule_asset_retirement(instance.cover_asset_id)


@receiver(pre_save, sender=BrandSettings)
def remember_previous_logo_asset(sender, instance, **kwargs):
    if instance.pk:
        instance._previous_logo_asset_id = (
            sender.objects.filter(pk=instance.pk)
            .values_list("logo_asset_id", flat=True)
            .first()
        )
    else:
        instance._previous_logo_asset_id = None


@receiver(post_save, sender=BrandSettings)
def retire_replaced_logo_asset(sender, instance, **kwargs):
    previous_id = getattr(instance, "_previous_logo_asset_id", None)
    if previous_id and previous_id != instance.logo_asset_id:
        _schedule_asset_retirement(previous_id)
    _restore_asset(instance.logo_asset_id)


@receiver(post_delete, sender=BrandSettings)
def retire_deleted_brand_setting(sender, instance, **kwargs):
    _schedule_asset_retirement(instance.logo_asset_id)


@receiver(pre_save, sender=BlogPostPage)
def remember_previous_blog_cover(sender, instance, **kwargs):
    if instance.pk:
        instance._previous_cover_asset_id = (
            sender.objects.filter(pk=instance.pk)
            .values_list("cover_asset_id", flat=True)
            .first()
        )
    else:
        instance._previous_cover_asset_id = None


@receiver(post_save, sender=BlogPostPage)
def retire_replaced_blog_cover(sender, instance, **kwargs):
    previous_id = getattr(instance, "_previous_cover_asset_id", None)
    if previous_id and previous_id != instance.cover_asset_id:
        _schedule_asset_retirement(previous_id)
    _restore_asset(instance.cover_asset_id)


@receiver(post_save, sender=CustomOrderInquiry)
def restore_custom_reference_asset(sender, instance, **kwargs):
    _restore_asset(instance.reference_asset_id)


def _schedule_asset_retirement(asset_id):
    if not asset_id:
        return
    _mark_asset_if_unreferenced(asset_id)


def _mark_asset_if_unreferenced(asset_id):
    asset = ImageAsset.objects.filter(pk=asset_id).first()
    if asset is None or _asset_is_referenced(asset_id):
        return
    if asset.status != ImageAsset.Status.DELETION_PENDING:
        asset.status = ImageAsset.Status.DELETION_PENDING
        asset.purge_after = timezone.now() + timedelta(days=ASSET_RECOVERY_DAYS)
        asset.save(update_fields=["status", "purge_after", "updated_at"])


def _restore_asset(asset_id):
    if not asset_id:
        return
    asset = ImageAsset.objects.filter(pk=asset_id).first()
    if asset and asset.status == ImageAsset.Status.DELETION_PENDING:
        asset.status = ImageAsset.Status.ACTIVE
        asset.purge_after = None
        asset.save(update_fields=["status", "purge_after", "updated_at"])


def _asset_is_referenced(asset_id):
    return (
        ProductImageAsset.objects.filter(asset_id=asset_id).exists()
        or BrandSettings.objects.filter(logo_asset_id=asset_id).exists()
        or BlogPostPage.objects.filter(cover_asset_id=asset_id).exists()
        or CustomOrderInquiry.objects.filter(reference_asset_id=asset_id).exists()
    )
