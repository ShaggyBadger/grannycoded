from django.db import migrations


def clear_product_thumbnail_cache(apps, schema_editor):
    Thumbnail = apps.get_model("easy_thumbnails", "Thumbnail")
    Thumbnail.objects.filter(source__name__startswith="products/").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("easy_thumbnails", "0002_thumbnaildimensions"),
        ("home", "0011_relink_legacy_product_images"),
    ]

    operations = [
        migrations.RunPython(
            clear_product_thumbnail_cache,
            migrations.RunPython.noop,
        ),
    ]
