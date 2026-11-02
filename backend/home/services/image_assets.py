"""Validated uploads for ULID-keyed public and private image assets."""

from pathlib import PurePosixPath

from django.core.exceptions import ValidationError

from home.models import ImageAsset


ALLOWED_IMAGE_SUFFIXES = {".avif", ".jpeg", ".jpg", ".png", ".webp"}


def save_uploaded_image(
    uploaded_file,
    *,
    visibility: str,
    category: str,
    display_name: str = "",
    source_path: str = "",
    asset_id: str | None = None,
) -> ImageAsset:
    """Save an uploaded image using its database ULID as its object filename."""
    original_name = PurePosixPath(
        str(getattr(uploaded_file, "name", "image")).replace("\\", "/")
    ).name[:255]
    if PurePosixPath(original_name).suffix.lower() not in ALLOWED_IMAGE_SUFFIXES:
        raise ValidationError("Upload a JPG, PNG, WebP, or AVIF image.")

    asset = ImageAsset(
        display_name=(display_name or original_name).strip()[:255],
        original_name=original_name,
        category=category,
        visibility=visibility,
        source_path=source_path,
    )
    if asset_id:
        asset.pk = asset_id
    if visibility == ImageAsset.Visibility.PUBLIC:
        asset.public_file = uploaded_file
    elif visibility == ImageAsset.Visibility.PRIVATE:
        asset.private_file = uploaded_file
    else:
        raise ValidationError("Choose a valid image access class.")
    asset.full_clean()
    asset.save()
    return asset
