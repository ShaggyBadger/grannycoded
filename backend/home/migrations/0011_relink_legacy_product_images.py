from django.db import migrations


def relink_legacy_product_images(apps, schema_editor):
    ProductImage = apps.get_model("catalogue", "ProductImage")
    ProductImageAsset = apps.get_model("home", "ProductImageAsset")

    for image in ProductImage.objects.all().iterator():
        asset_name = (
            ProductImageAsset.objects.filter(
                product_id=image.product_id,
                asset__visibility="public",
                asset__status="active",
            )
            .order_by("position", "pk")
            .values_list("asset__public_file", flat=True)
            .first()
        )
        if asset_name and image.original != asset_name:
            ProductImage.objects.filter(pk=image.pk).update(original=asset_name)


class Migration(migrations.Migration):
    dependencies = [
        (
            "catalogue",
            "0032_category_exclude_from_menu_category_long_description",
        ),
        ("home", "0010_imageasset_blogpostpage_cover_asset_and_more"),
    ]

    operations = [
        migrations.RunPython(
            relink_legacy_product_images,
            migrations.RunPython.noop,
        ),
    ]
