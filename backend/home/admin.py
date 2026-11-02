from django.contrib import admin

from home.models import ImageAsset, ProductImageAsset


@admin.register(ImageAsset)
class ImageAssetAdmin(admin.ModelAdmin):
    list_display = ("display_name", "category", "visibility", "status", "created_at")
    list_filter = ("category", "visibility", "status")
    search_fields = ("display_name", "original_name", "id")
    fields = (
        "display_name",
        "category",
        "visibility",
        "public_file",
        "id",
        "original_name",
        "content_type",
        "size_bytes",
        "sha256",
        "source_path",
        "status",
        "created_at",
        "updated_at",
        "purge_after",
    )
    readonly_fields = (
        "id",
        "original_name",
        "content_type",
        "size_bytes",
        "sha256",
        "status",
        "created_at",
        "updated_at",
        "purge_after",
    )

    def has_delete_permission(self, request, obj=None):
        return False

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "visibility":
            kwargs["choices"] = [
                (
                    ImageAsset.Visibility.PUBLIC.value,
                    ImageAsset.Visibility.PUBLIC.label,
                )
            ]
        elif db_field.name == "category":
            kwargs["choices"] = [
                choice
                for choice in ImageAsset.Category.choices
                if choice[0] != ImageAsset.Category.CUSTOM_REFERENCE
            ]
        return super().formfield_for_choice_field(db_field, request, **kwargs)


@admin.register(ProductImageAsset)
class ProductImageAssetAdmin(admin.ModelAdmin):
    list_display = ("product", "asset", "position")
    list_select_related = ("product", "asset")
    search_fields = ("product__title", "asset__display_name", "asset__id")
    autocomplete_fields = ("asset", "product")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "asset":
            kwargs["queryset"] = ImageAsset.objects.filter(
                visibility=ImageAsset.Visibility.PUBLIC,
                status=ImageAsset.Status.ACTIVE,
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
