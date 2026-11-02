"""Upload GrannyCoded images and map Linode objects to database assets."""

import json
from pathlib import Path
import re
from urllib.parse import urlparse

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db.models import F
from oscar.core.loading import get_model
from PIL import Image as PillowImage
from wagtail.models import Site

from home.asset_ids import ULID_PATTERN, new_ulid
from home.models import BrandSettings, ImageAsset, ProductImageAsset
from home.services.image_assets import save_uploaded_image


LISTING_URL_PATTERN = re.compile(r"https?://www\.etsy\.com/listing/\d+/[^\s\"']*")


class Command(BaseCommand):
    help = "Upload GrannyCoded product photos and logo to public image storage."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-dir",
            type=Path,
            default=Path(settings.BASE_DIR) / "static" / "images",
            help="Directory containing the logo and product images.",
        )
        parser.add_argument(
            "--manifest",
            type=Path,
            default=Path(settings.BASE_DIR) / "home" / "catalog_image_manifest.json",
            help="Image metadata manifest used to bootstrap other databases.",
        )
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Upload files and update the database; default is a dry run.",
        )

    def handle(self, *args, **options):
        source_dir: Path = options["source_dir"]
        product_files = sorted((source_dir / "products").glob("*.webp"))
        logo_path = source_dir / "grannycoded_logo.avif"
        if not product_files or not logo_path.is_file():
            raise CommandError(
                "Expected the product WebPs and GrannyCoded logo AVIF in the source directory."
            )

        if not options["execute"]:
            self.stdout.write(
                f"Dry run: {len(product_files)} product photos and the logo are ready to migrate."
            )
            self.stdout.write("Pass --execute to upload and update the local database.")
            return

        if not settings.USE_LINODE_OBJECT_STORAGE:
            raise CommandError(
                "Linode storage is not active in this Django process. Enable it in the local "
                ".env and recreate the web container before uploading."
            )

        import pillow_heif

        pillow_heif.register_heif_opener()

        Product = get_model("catalogue", "Product")
        ProductAttribute = get_model("catalogue", "ProductAttribute")
        ProductAttributeValue = get_model("catalogue", "ProductAttributeValue")
        product_class = get_model("catalogue", "ProductClass").objects.get(
            slug="handmade-goods"
        )
        source_attribute = ProductAttribute.objects.get(
            product_class=product_class,
            code="source_listing_url",
        )
        products_by_listing_id = {
            self._listing_id(value.value_text): value.product
            for value in ProductAttributeValue.objects.filter(
                attribute=source_attribute
            ).select_related("product")
        }
        manifest_path: Path = options["manifest"]
        manifest = self._read_manifest(manifest_path)
        uploaded = 0
        already_present = 0

        for image_path in product_files:
            listing_url = self._listing_url_for_image(image_path)
            listing_id = self._listing_id(listing_url)
            product = products_by_listing_id.get(listing_id)
            if product is None:
                raise CommandError(
                    f"No Oscar product matches the image source for listing {listing_id}."
                )

            source_path = image_path.relative_to(Path(settings.BASE_DIR)).as_posix()
            entry = manifest["products"].get(listing_id, {})
            asset_id = entry.get("asset_ulid") or entry.get("ulid") or new_ulid()
            entry.update(
                {
                    "ulid": asset_id,
                    "asset_ulid": asset_id,
                    "display_name": product.title,
                    "alt_text": product.title,
                    "product_slug": product.slug,
                    "listing_url": listing_url,
                    "source_path": source_path,
                }
            )
            if not entry.get("asset_storage_name"):
                if entry.get("storage_name"):
                    entry["legacy_storage_name"] = entry["storage_name"]
                entry["storage_name"] = self._expected_storage_name(
                    ImageAsset.Category.PRODUCT, asset_id, image_path
                )
                entry["asset_storage_name"] = entry["storage_name"]
            manifest["products"][listing_id] = entry
            self._write_manifest(manifest_path, manifest)

            asset, was_present = self._ensure_asset(
                image_path,
                asset_id=asset_id,
                category=ImageAsset.Category.PRODUCT,
                display_name=product.title,
                source_path=source_path,
                existing_entry=entry,
            )
            ProductImageAsset.objects.update_or_create(
                product=product,
                position=0,
                defaults={"asset": asset, "alt_text": product.title},
            )
            self._clear_legacy_image_attribute(product)
            manifest["products"][listing_id] = self._asset_manifest_entry(
                asset,
                listing_url=listing_url,
                product_slug=product.slug,
                alt_text=product.title,
            )
            self._write_manifest(manifest_path, manifest)
            if was_present:
                already_present += 1
            else:
                uploaded += 1

        logo_entry = manifest.get("logo") or {}
        logo_id = logo_entry.get("asset_ulid") or logo_entry.get("ulid") or new_ulid()
        if not logo_entry.get("asset_storage_name"):
            if logo_entry.get("storage_name"):
                logo_entry["legacy_storage_name"] = logo_entry["storage_name"]
            logo_entry["storage_name"] = self._expected_storage_name(
                ImageAsset.Category.BRAND, logo_id, logo_path
            )
            logo_entry["asset_storage_name"] = logo_entry["storage_name"]
        logo_asset, logo_was_present = self._ensure_asset(
            logo_path,
            asset_id=logo_id,
            category=ImageAsset.Category.BRAND,
            display_name="GrannyCoded logo",
            source_path=logo_path.relative_to(Path(settings.BASE_DIR)).as_posix(),
            existing_entry=logo_entry,
        )
        brand_settings, _ = BrandSettings.objects.get_or_create(
            site=Site.objects.get(is_default_site=True)
        )
        if brand_settings.logo_asset_id != logo_asset.pk:
            brand_settings.logo_asset = logo_asset
            brand_settings.save(update_fields=["logo_asset"])

        with PillowImage.open(logo_path) as source_image:
            width, height = source_image.size
        manifest["logo"] = {
            **self._asset_manifest_entry(logo_asset),
            "width": width,
            "height": height,
        }
        self._write_manifest(manifest_path, manifest)

        self.stdout.write(
            self.style.SUCCESS(
                f"Image migration verified: {uploaded} product photos uploaded, "
                f"{already_present} already present, logo "
                f"{'already present' if logo_was_present else 'uploaded'}."
            )
        )

    @staticmethod
    def _ensure_asset(
        image_path: Path,
        *,
        asset_id: str,
        category: str,
        display_name: str,
        source_path: str,
        existing_entry: dict,
    ) -> tuple[ImageAsset, bool]:
        from django.core.files.storage import storages

        if not ULID_PATTERN.fullmatch(asset_id):
            raise CommandError(f"Image asset ID is not a ULID: {asset_id}.")
        storage = storages["public_images"]
        asset = ImageAsset.objects.filter(pk=asset_id).first()
        if asset:
            if (
                asset.visibility != ImageAsset.Visibility.PUBLIC
                or asset.category != category
                or not storage.exists(asset.public_file.name)
            ):
                raise CommandError(
                    f"Image asset {asset_id} exists but is not a verified public object."
                )
            asset.display_name = display_name
            asset.source_path = source_path
            asset.status = ImageAsset.Status.ACTIVE
            asset.purge_after = None
            asset.save(
                update_fields=[
                    "display_name",
                    "source_path",
                    "status",
                    "purge_after",
                    "updated_at",
                ]
            )
            return asset, True

        storage_name = existing_entry.get("storage_name")
        if storage_name and storage.exists(storage_name):
            asset = Command._register_existing_asset(
                image_path,
                asset_id=asset_id,
                storage_name=storage_name,
                category=category,
                display_name=display_name,
                source_path=source_path,
            )
            return asset, True

        try:
            with image_path.open("rb") as source:
                asset = save_uploaded_image(
                    File(source),
                    visibility=ImageAsset.Visibility.PUBLIC,
                    category=category,
                    display_name=display_name,
                    source_path=source_path,
                    asset_id=asset_id,
                )
        except Exception as exc:
            raise CommandError(
                f"Could not upload {image_path.name}: {type(exc).__name__}."
            ) from exc

        if not storage.exists(asset.public_file.name):
            raise CommandError(
                f"Uploaded object could not be verified for image asset {asset_id}."
            )
        return asset, False

    @staticmethod
    def _register_existing_asset(
        image_path: Path,
        *,
        asset_id: str,
        storage_name: str,
        category: str,
        display_name: str,
        source_path: str,
    ) -> ImageAsset:
        import mimetypes
        from hashlib import sha256

        contents = image_path.read_bytes()
        asset = ImageAsset(
            pk=asset_id,
            display_name=display_name,
            original_name=image_path.name,
            category=category,
            visibility=ImageAsset.Visibility.PUBLIC,
            source_path=source_path,
            content_type=mimetypes.guess_type(image_path.name)[0] or "application/octet-stream",
            size_bytes=len(contents),
            sha256=sha256(contents).hexdigest(),
            status=ImageAsset.Status.ACTIVE,
        )
        asset.public_file.name = storage_name
        asset.save(force_insert=True)
        return asset

    @staticmethod
    def _asset_manifest_entry(
        asset: ImageAsset,
        *,
        listing_url: str = "",
        product_slug: str = "",
        alt_text: str = "",
    ) -> dict:
        entry = {
            "ulid": asset.pk,
            "asset_ulid": asset.pk,
            "storage_name": asset.public_file.name,
            "asset_storage_name": asset.public_file.name,
            "display_name": asset.display_name,
            "source_path": asset.source_path,
            "content_type": asset.content_type,
            "size_bytes": asset.size_bytes,
            "sha256": asset.sha256,
        }
        if listing_url:
            entry.update(
                {
                    "alt_text": alt_text,
                    "listing_url": listing_url,
                    "product_slug": product_slug,
                }
            )
        return entry

    @staticmethod
    def _expected_storage_name(category: str, asset_id: str, image_path: Path) -> str:
        return f"{category}/{asset_id}{image_path.suffix.lower()}"

    @staticmethod
    def _read_manifest(manifest_path: Path) -> dict:
        if not manifest_path.is_file():
            return {"version": 2, "products": {}, "logo": None}
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"Image manifest is invalid JSON: {manifest_path}") from exc
        manifest.setdefault("version", 2)
        manifest.setdefault("products", {})
        manifest.setdefault("logo", None)
        return manifest

    @staticmethod
    def _write_manifest(path: Path, manifest: dict) -> None:
        manifest["version"] = 2
        path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _listing_url_for_image(image_path: Path) -> str:
        sidecar = image_path.with_suffix(image_path.suffix + ".json")
        try:
            metadata = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f"Image provenance file is missing or invalid: {sidecar}") from exc
        match = LISTING_URL_PATTERN.search(metadata.get("prompt", ""))
        if not match:
            raise CommandError(f"Image provenance has no Etsy listing URL: {sidecar}")
        return match.group(0).rstrip(".,;)")

    @staticmethod
    def _listing_id(url: str) -> str:
        parts = urlparse(url).path.strip("/").split("/")
        return parts[1] if len(parts) > 1 and parts[0] == "listing" else ""

    @staticmethod
    def _clear_legacy_image_attribute(product) -> None:
        value = product.attribute_values.filter(
            attribute__code="static_image_path"
        ).first()
        if value and value.value_text:
            value.value_text = ""
            value.save(update_fields=["value_text"])
