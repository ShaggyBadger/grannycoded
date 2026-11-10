from decimal import Decimal
from hashlib import sha256
import mimetypes
from pathlib import PurePosixPath

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Prefetch
from django.urls import reverse
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from taggit.models import TaggedItemBase
from wagtail.admin.panels import FieldPanel
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting
from wagtail.fields import RichTextField
from wagtail.models import Page

from home.asset_ids import new_ulid
from home.storage import PrivateImageStorage, PublicImageStorage


def public_image_upload_to(instance, filename: str) -> str:
    suffix = PurePosixPath(filename).suffix.lower()
    return f"{instance.category}/{instance.pk}{suffix}"


def private_image_upload_to(instance, filename: str) -> str:
    suffix = PurePosixPath(filename).suffix.lower()
    return f"custom-order-references/{instance.pk}{suffix}"


class HomePage(Page):
    """Starting page type for the public site."""

    intro = RichTextField(blank=True)
    hero_heading = models.CharField(
        max_length=120,
        default="Found quilts. Remade to be worn again.",
    )
    hero_copy = models.TextField(
        default=(
            "We find quilts at thrift shops and turn them into one-of-a-kind "
            "garments and accessories. Every piece carries its own past."
        )
    )
    story_heading = models.CharField(
        max_length=120,
        default="A new life for a well-loved textile.",
    )
    story_copy = models.TextField(
        default=(
            "GrannyCoded starts with quilts found in thrift shops and reimagines "
            "them as wearable pieces and useful keepsakes."
        )
    )

    content_panels = Page.content_panels + [
        FieldPanel("hero_heading"),
        FieldPanel("hero_copy"),
        FieldPanel("intro"),
        FieldPanel("story_heading"),
        FieldPanel("story_copy"),
    ]

    subpage_types = ["home.BlogIndexPage", "home.PolicyPage"]

    def get_context(self, request):
        context = super().get_context(request)
        from oscar.core.loading import get_model

        Product = get_model("catalogue", "Product")
        products = list(
            Product.objects.browsable()
            .exclude(structure=Product.CHILD)
            .select_related("product_class")
            .prefetch_related(
                "stockrecords",
                "images",
                "managed_images__asset",
                Prefetch(
                    "children",
                    queryset=Product.objects.public().prefetch_related("stockrecords"),
                    to_attr="_prefetched_public_children",
                ),
            )
            .order_by("-priority", "-date_created")[:12]
        )

        def has_stock(product):
            if product.structure == Product.PARENT:
                stock_records = (
                    record
                    for child in product.get_public_children()
                    for record in child.stockrecords.all()
                )
            else:
                stock_records = iter(product.stockrecords.all())
            return any(
                (record.num_in_stock or 0) - (record.num_allocated or 0) > 0
                for record in stock_records
            )

        available_products = [product for product in products if has_stock(product)]
        context["featured_product"] = available_products[0] if available_products else None
        context["shop_preview"] = available_products[:3]
        context["story_product"] = next(
            (
                product
                for product in products
                if product.slug == "the-mimi-coat-blue-ribbon-winning-quilt"
            ),
            context["featured_product"],
        )
        context["recent_posts"] = (
            BlogPostPage.objects.live()
            .order_by("-first_published_at")
            .specific()[:3]
        )
        return context

    class Meta:
        verbose_name = "home page"


class BlogIndexPage(Page):
    """Index of GrannyCoded blog posts."""

    POSTS_PER_PAGE = 10

    intro = models.TextField(blank=True)

    parent_page_types = ["home.HomePage"]
    subpage_types = ["home.BlogPostPage"]
    content_panels = Page.content_panels + [FieldPanel("intro")]

    def get_context(self, request):
        context = super().get_context(request)
        posts = (
            BlogPostPage.objects.child_of(self)
            .live()
            .select_related("cover_asset", "cover_image")
            .prefetch_related("tags")
            .order_by("-first_published_at")
            .specific()
        )
        page_obj = Paginator(posts, self.POSTS_PER_PAGE).get_page(
            request.GET.get("page")
        )
        page_posts = list(page_obj.object_list)
        context["page_obj"] = page_obj
        context["is_paginated"] = page_obj.has_other_pages()
        context["featured_post"] = (
            page_posts[0]
            if page_obj.number == 1 and page_posts
            else None
        )
        context["posts"] = (
            page_posts[1:]
            if page_obj.number == 1 and page_posts
            else page_posts
        )
        return context


class PolicyPage(Page):
    """Editable customer-facing policy and service-information pages."""

    intro = models.TextField(blank=True)
    body = RichTextField(blank=True)
    support_email = models.EmailField(default="grannycoded@gmail.com")

    parent_page_types = ["home.HomePage"]
    subpage_types = []
    content_panels = Page.content_panels + [
        FieldPanel("intro", heading="Introduction"),
        FieldPanel("body", heading="Policy content"),
        FieldPanel("support_email", heading="Customer support email"),
    ]

    class Meta:
        verbose_name = "policy page"


class ImageAsset(models.Model):
    """A ULID-keyed image with its human-readable name and access class."""

    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"

    class Category(models.TextChoices):
        BRAND = "brand", "Brand"
        PRODUCT = "products", "Product"
        EDITORIAL = "editorial", "Editorial"
        CUSTOM_REFERENCE = "custom-order-references", "Custom-order reference"

    class Status(models.TextChoices):
        UPLOADING = "uploading", "Uploading"
        ACTIVE = "active", "Active"
        DELETION_PENDING = "deletion_pending", "Deletion pending"
        DELETED = "deleted", "Deleted from storage"
        FAILED = "failed", "Upload failed"

    id = models.CharField(
        primary_key=True,
        max_length=26,
        default=new_ulid,
        editable=False,
    )
    display_name = models.CharField(max_length=255)
    original_name = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=32, choices=Category.choices)
    visibility = models.CharField(
        max_length=8,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
        db_index=True,
    )
    public_file = models.ImageField(
        upload_to=public_image_upload_to,
        storage=PublicImageStorage(),
        blank=True,
    )
    private_file = models.ImageField(
        upload_to=private_image_upload_to,
        storage=PrivateImageStorage(),
        blank=True,
        editable=False,
    )
    source_path = models.CharField(max_length=512, blank=True, db_index=True)
    content_type = models.CharField(max_length=100, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPLOADING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    purge_after = models.DateTimeField(null=True, blank=True, db_index=True)
    purge_attempts = models.PositiveIntegerField(default=0)
    last_purge_error = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "purge_after"]),
            models.Index(fields=["visibility", "category"]),
        ]

    def __str__(self) -> str:
        return self.display_name

    def clean(self):
        super().clean()
        if (
            self.category == self.Category.CUSTOM_REFERENCE
            and self.visibility != self.Visibility.PRIVATE
        ):
            raise ValidationError("Custom-order reference images must remain private.")
        if (
            self.category != self.Category.CUSTOM_REFERENCE
            and self.visibility != self.Visibility.PUBLIC
        ):
            raise ValidationError("Brand, product, and editorial images must be public.")
        if self.visibility == self.Visibility.PUBLIC:
            if not self.public_file or self.private_file:
                raise ValidationError("Public assets need a public image file only.")
        elif not self.private_file or self.public_file:
            raise ValidationError("Private assets need a private image file only.")

    @property
    def file(self):
        return (
            self.private_file
            if self.visibility == self.Visibility.PRIVATE
            else self.public_file
        )

    def get_url(self) -> str:
        if self.status != self.Status.ACTIVE:
            return ""
        if self.visibility == self.Visibility.PRIVATE:
            return reverse("private_image_asset", kwargs={"asset_id": self.pk})
        return self.public_file.url

    def save(self, *args, **kwargs):
        uploaded = self.file
        upload_file = uploaded.file if uploaded and not uploaded._committed else None
        if upload_file:
            original_name = PurePosixPath(
                uploaded.name.replace("\\", "/")
            ).name[:255]
            self.original_name = self.original_name or original_name
            self.display_name = self.display_name or original_name
            self.content_type = (
                mimetypes.guess_type(original_name)[0]
                or "application/octet-stream"
            )
            self.size_bytes = upload_file.size
            self.sha256 = _uploaded_file_sha256(upload_file)
            self.status = self.Status.ACTIVE
        super().save(*args, **kwargs)


def _uploaded_file_sha256(uploaded_file) -> str:
    try:
        original_position = uploaded_file.tell()
    except (AttributeError, OSError):
        original_position = 0
    digest = sha256()
    uploaded_file.seek(0)
    for chunk in uploaded_file.chunks():
        digest.update(chunk)
    uploaded_file.seek(original_position)
    return digest.hexdigest()


class ProductImageAsset(models.Model):
    """An image linked to an Oscar product, with per-product alternative text."""

    product = models.ForeignKey(
        "catalogue.Product",
        on_delete=models.CASCADE,
        related_name="managed_images",
    )
    asset = models.ForeignKey(
        ImageAsset,
        on_delete=models.PROTECT,
        related_name="product_links",
    )
    alt_text = models.CharField(max_length=255)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "position"],
                name="home_product_image_position_unique",
            )
        ]

    def clean(self):
        super().clean()
        if self.asset_id and (
            self.asset.visibility != ImageAsset.Visibility.PUBLIC
            or self.asset.status != ImageAsset.Status.ACTIVE
        ):
            raise ValidationError("Products can only use active public image assets.")


class PendingImageDeletion(models.Model):
    """An object queued for deletion after its recovery grace period."""

    class StorageAlias(models.TextChoices):
        PUBLIC = "default", "Public image storage"
        PRIVATE = "private_images", "Private image storage"

    storage_alias = models.CharField(max_length=20, choices=StorageAlias.choices)
    object_name = models.CharField(max_length=512)
    delete_after = models.DateTimeField(db_index=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["storage_alias", "object_name"],
                name="home_pending_image_delete_unique",
            )
        ]
        ordering = ["delete_after", "pk"]


class CustomOrderInquiry(models.Model):
    """A customer request that the maker reviews before quoting custom work."""

    class Status(models.TextChoices):
        NEW = "new", "New"
        REVIEWING = "reviewing", "Reviewing"
        QUOTED = "quoted", "Quoted"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        CONVERTED = "converted", "Converted to order"

    name = models.CharField(max_length=120)
    email = models.EmailField()
    request_details = models.TextField(max_length=5000)
    reference_photo = models.ImageField(
        upload_to="custom-order-inquiries/%Y/%m/",
        blank=True,
        storage=PrivateImageStorage(),
    )
    reference_photo_name = models.CharField(max_length=255, blank=True)
    reference_asset = models.ForeignKey(
        ImageAsset,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="custom_inquiries",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
    )
    quoted_total = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    quoted_shipping = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    shipping_note = models.CharField(max_length=255, blank=True)
    maker_notes = models.TextField(blank=True)
    order = models.ForeignKey(
        "order.Order",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="custom_order_inquiries",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Custom inquiry from {self.name} ({self.get_status_display()})"


class BlogPostPage(Page):
    """An article in the GrannyCoded blog."""

    excerpt = models.CharField(max_length=280, blank=True)
    body = RichTextField(blank=True)
    cover_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    cover_asset = models.ForeignKey(
        ImageAsset,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="blog_covers",
    )
    tags = ClusterTaggableManager(through="home.BlogPostPageTag", blank=True)

    parent_page_types = ["home.BlogIndexPage"]
    subpage_types = []
    content_panels = [
        FieldPanel("title", heading="Post title"),
        FieldPanel(
            "excerpt",
            heading="Short summary",
            help_text="A brief introduction shown on the blog and search results.",
        ),
        FieldPanel(
            "body",
            heading="Post body",
            help_text="Write and format the full story with the toolbar.",
        ),
        FieldPanel("tags", heading="Tags"),
        FieldPanel(
            "cover_upload",
            heading="Upload a cover image",
        ),
    ]

    def clean(self):
        super().clean()
        if self.cover_asset_id and (
            self.cover_asset.visibility != ImageAsset.Visibility.PUBLIC
            or self.cover_asset.status != ImageAsset.Status.ACTIVE
        ):
            raise ValidationError("Blog covers must use active public image assets.")


class BlogPostPageTag(TaggedItemBase):
    content_object = ParentalKey(
        "home.BlogPostPage",
        related_name="tagged_items",
        on_delete=models.CASCADE,
    )


@register_setting
class BrandSettings(BaseSiteSetting):
    """Site-wide social links and short maker introduction."""

    maker_note = models.TextField(blank=True)
    logo_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    logo_asset = models.ForeignKey(
        ImageAsset,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="brand_settings",
    )
    instagram_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    pinterest_url = models.URLField(blank=True)
    tiktok_url = models.URLField(blank=True)

    panels = [
        FieldPanel("maker_note"),
        FieldPanel("logo_asset"),
        FieldPanel("logo_image"),
        FieldPanel("instagram_url"),
        FieldPanel("facebook_url"),
        FieldPanel("pinterest_url"),
        FieldPanel("tiktok_url"),
    ]

    def clean(self):
        super().clean()
        if self.logo_asset_id and (
            self.logo_asset.visibility != ImageAsset.Visibility.PUBLIC
            or self.logo_asset.status != ImageAsset.Status.ACTIVE
        ):
            raise ValidationError("The site logo must use an active public image asset.")


class CheckoutSession(models.Model):
    """A Stripe Checkout attempt, snapshotted from the basket at creation.

    Line prices and titles are stored here so a later catalog edit cannot
    change what the shopper was shown or what they paid.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending payment"
        PAID = "paid", "Paid"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"
        FAILED = "failed", "Failed"

    id = models.CharField(
        primary_key=True,
        max_length=26,
        default=new_ulid,
        editable=False,
    )
    stripe_session_id = models.CharField(
        max_length=255, unique=True, null=True, blank=True
    )
    basket_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    email = models.EmailField(blank=True)
    shipping_name = models.CharField(max_length=255, blank=True)
    shipping_address = models.JSONField(default=dict, blank=True)
    currency = models.CharField(max_length=3, default="usd")
    total_incl_tax = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    order_number = models.CharField(max_length=64, blank=True)
    expires_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Checkout {self.pk} ({self.get_status_display()})"

    @property
    def is_open(self) -> bool:
        return self.status == self.Status.PENDING


class CheckoutLine(models.Model):
    """A snapshotted basket line for one checkout attempt."""

    session = models.ForeignKey(
        CheckoutSession,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product = models.ForeignKey(
        "catalogue.Product",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="checkout_lines",
    )
    product_title = models.CharField(max_length=255)
    partner_sku = models.CharField(max_length=64, blank=True)
    quantity = models.PositiveIntegerField()
    unit_price_incl_tax = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="usd")

    class Meta:
        ordering = ["pk"]

    def __str__(self) -> str:
        return f"{self.quantity} x {self.product_title}"

    @property
    def line_total_incl_tax(self) -> Decimal:
        return self.unit_price_incl_tax * self.quantity


class StockReservation(models.Model):
    """Stock held for an open checkout attempt.

    Available stock is the stock record's balance minus unexpired reservations,
    so a one-of-a-kind piece cannot be sold twice while a payment page is open.
    """

    session = models.ForeignKey(
        CheckoutSession,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    product = models.ForeignKey(
        "catalogue.Product",
        on_delete=models.CASCADE,
        related_name="stock_reservations",
    )
    quantity = models.PositiveIntegerField()
    expires_at = models.DateTimeField(db_index=True)
    released_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["pk"]
        indexes = [
            models.Index(fields=["product", "released_at", "expires_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.quantity} held for {self.product_id}"


class StripeEvent(models.Model):
    """A received Stripe webhook event, recorded for idempotency."""

    id = models.CharField(primary_key=True, max_length=255)
    event_type = models.CharField(max_length=128)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self) -> str:
        return f"{self.event_type} ({self.pk})"
