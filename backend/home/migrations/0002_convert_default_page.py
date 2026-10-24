from django.db import migrations


def convert_default_site_page(apps, schema_editor):
    """Make Wagtail's initial site root use the starter's editable page type."""
    ContentType = apps.get_model("contenttypes", "ContentType")
    HomePage = apps.get_model("home", "HomePage")
    Page = apps.get_model("wagtailcore", "Page")
    Site = apps.get_model("wagtailcore", "Site")

    site = Site.objects.filter(is_default_site=True).first() or Site.objects.first()
    if site is None:
        return

    page = Page.objects.get(pk=site.root_page_id)
    if page.depth <= 1 or HomePage.objects.filter(pk=page.pk).exists():
        return

    home_page_type, _ = ContentType.objects.get_or_create(
        app_label="home",
        model="homepage",
    )
    Page.objects.filter(pk=page.pk).update(content_type_id=home_page_type.pk)
    home_page_table = schema_editor.quote_name(HomePage._meta.db_table)
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            f"INSERT INTO {home_page_table} (page_ptr_id, intro) VALUES (%s, %s)",
            [page.pk, ""],
        )


def restore_default_page_type(apps, schema_editor):
    """Restore the generic Wagtail Page content type when reversing this migration."""
    ContentType = apps.get_model("contenttypes", "ContentType")
    HomePage = apps.get_model("home", "HomePage")
    Page = apps.get_model("wagtailcore", "Page")
    Site = apps.get_model("wagtailcore", "Site")

    site = Site.objects.filter(is_default_site=True).first() or Site.objects.first()
    if site is None:
        return

    home_page_table = schema_editor.quote_name(HomePage._meta.db_table)
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            f"DELETE FROM {home_page_table} WHERE page_ptr_id = %s",
            [site.root_page_id],
        )
    page_type, _ = ContentType.objects.get_or_create(
        app_label="wagtailcore",
        model="page",
    )
    Page.objects.filter(pk=site.root_page_id).update(content_type_id=page_type.pk)


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(convert_default_site_page, restore_default_page_type),
    ]
