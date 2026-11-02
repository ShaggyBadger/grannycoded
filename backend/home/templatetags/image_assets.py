from django import template

register = template.Library()


@register.simple_tag
def primary_product_image(product):
    """Return the first active managed image for a product."""
    if product is None:
        return None

    prefetched = getattr(product, "_prefetched_objects_cache", {}).get(
        "managed_images"
    )
    images = (
        prefetched
        if prefetched is not None
        else product.managed_images.select_related("asset").order_by("position", "pk")
    )
    return next(
        (
            image
            for image in images
            if image.asset.status == image.asset.Status.ACTIVE
        ),
        None,
    )
