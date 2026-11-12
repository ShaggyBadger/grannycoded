import json
from datetime import timedelta
from decimal import Decimal
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree

from django.conf import settings
from django.contrib.sites.models import Site as DjangoSite
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from easy_thumbnails.models import Source, Thumbnail
from PIL import Image
from wagtail.contrib.redirects.models import Redirect
from wagtail.models import Site

from home.asset_ids import new_ulid
from home.management.commands.purge_pending_images import Command as PurgePendingImages
from home.models import (
    BlogIndexPage,
    BlogPostPage,
    BrandSettings,
    CustomOrderInquiry,
    HomePage,
    ImageAsset,
    PendingImageDeletion,
    PolicyPage,
    ProductImageAsset,
)
from home.storage import ULIDFileSystemStorage
from home.wagtail_hooks import BlogPostsMenuItem
from oscar.core.loading import get_model


class StorefrontTests(TestCase):
    def setUp(self):
        self.home = Site.objects.get(is_default_site=True).root_page.specific
        self.product_class = get_model("catalogue", "ProductClass").objects.get(
            slug="handmade-goods"
        )
        self.partner = get_model("partner", "Partner").objects.get(
            code="grannycoded"
        )
        self.category = get_model("catalogue", "Category").objects.get(
            slug="wearables"
        )
        self.Product = get_model("catalogue", "Product")
        self.ProductImage = get_model("catalogue", "ProductImage")
        self.StockRecord = get_model("partner", "StockRecord")
        self.ProductAttribute = get_model("catalogue", "ProductAttribute")
        self.ProductAttributeValue = get_model("catalogue", "ProductAttributeValue")

    def test_uploaded_image_names_are_monotonic_ulids(self):
        first = new_ulid()
        second = new_ulid()
        self.assertRegex(first, r"^[0-9A-HJKMNP-TV-Z]{26}$")
        self.assertLess(first, second)

        object_name = ULIDFileSystemStorage().get_available_name(
            "products/original-photo.webp"
        )
        self.assertRegex(Path(object_name).stem, r"^[0-9A-HJKMNP-TV-Z]{26}$")
        thumbnail_name = (
            "products/01ARZ3NDEKTSV4RRFFQ69G5FAV.webp.70x70_q85.jpg"
        )
        self.assertEqual(
            ULIDFileSystemStorage().get_available_name(thumbnail_name),
            thumbnail_name,
        )

    def create_product(
        self,
        *,
        slug="mimi-quilt-coat",
        title="Mimi Quilt Coat",
        price=Decimal("179.00"),
        stock=1,
        is_public=True,
        one_of_a_kind=True,
    ):
        product = self.Product.objects.create(
            title=title,
            slug=slug,
            description="A handmade piece created from a found quilt.",
            product_class=self.product_class,
            is_public=is_public,
        )
        product.categories.add(self.category)
        self.StockRecord.objects.create(
            product=product,
            partner=self.partner,
            partner_sku=slug,
            price_currency="USD",
            price=price,
            num_in_stock=stock,
            num_allocated=0,
        )
        one_of_a_kind_attribute = self.ProductAttribute.objects.get(
            product_class=self.product_class,
            code="one_of_a_kind",
        )
        self.ProductAttributeValue.objects.create(
            product=product,
            attribute=one_of_a_kind_attribute,
            value_boolean=one_of_a_kind,
        )
        image_path_attribute = self.ProductAttribute.objects.get(
            product_class=self.product_class,
            code="static_image_path",
        )
        self.ProductAttributeValue.objects.create(
            product=product,
            attribute=image_path_attribute,
            value_text="images/products/the-mimi-coat-blue-ribbon-winning-quilt.webp",
        )
        image_alt_attribute = self.ProductAttribute.objects.get(
            product_class=self.product_class,
            code="image_alt",
        )
        self.ProductAttributeValue.objects.create(
            product=product,
            attribute=image_alt_attribute,
            value_text="A handmade quilt coat",
        )
        return product

    def test_default_site_root_is_the_editable_home_page(self):
        self.assertIsInstance(self.home, HomePage)

    def test_home_page_renders_brand_story_and_oscar_catalogue_preview(self):
        self.create_product()

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Found quilts. Remade to be worn again.")
        self.assertContains(response, 'href="/shop/"')
        self.assertContains(response, 'aria-controls="site-nav"')
        self.assertContains(response, 'id="site-nav"')
        self.assertContains(response, "static/js/site-navigation.js")
        self.assertNotContains(response, "Shop one-offs")
        self.assertContains(response, "Mimi Quilt Coat")
        self.assertNotContains(response, "Shipping &amp; Returns", html=False)

    def test_shipping_returns_page_renders_the_approved_customer_terms(self):
        page = PolicyPage.objects.live().get(slug="shipping-returns")

        response = self.client.get(page.get_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ready-made orders ship within 3 business days")
        self.assertContains(response, "30 calendar days of delivery")
        self.assertContains(response, "unworn other than trying on")
        self.assertContains(response, "return shipping")
        self.assertContains(response, "full refund")
        self.assertContains(response, "materials already purchased")
        self.assertContains(response, 'href="mailto:grannycoded@gmail.com"', html=False)
        # The return policy is linked from the footer so shoppers can find it
        # before checkout, not only by guessing the URL.
        self.assertContains(response, 'href="/shipping-returns/"', html=False)

        editor = get_user_model().objects.create_superuser(
            username="policy-editor",
            email="policy-editor@example.com",
            password="test-password",
        )
        self.client.force_login(editor)
        edit_response = self.client.get(f"/admin/pages/{page.pk}/edit/")
        self.assertEqual(edit_response.status_code, 200)
        self.assertContains(edit_response, "Policy content")

    def test_shop_catalogue_links_to_shipping_and_returns_policy(self):
        policy_page = PolicyPage.objects.live().get(slug="shipping-returns")

        response = self.client.get(reverse("catalogue:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "See our Shipping &amp; Returns policy", html=False)
        self.assertContains(
            response,
            f'href="{policy_page.get_url()}"',
            html=False,
        )

    def test_privacy_page_explains_current_data_handling_and_is_linked(self):
        page = PolicyPage.objects.live().get(slug="privacy")

        response = self.client.get(page.get_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "optional reference photo")
        self.assertContains(response, "stored privately")
        self.assertContains(response, "do not currently expire automatically")
        self.assertContains(response, "marked for deletion with a 30-day recovery period")
        self.assertContains(response, "necessary session and security cookies")
        self.assertContains(response, "Online payments are processed by Stripe")
        self.assertContains(response, "Google Analytics")
        self.assertContains(response, "Google may receive a hashed copy")
        self.assertContains(response, "do not sell personal information")
        self.assertContains(response, 'href="mailto:grannycoded@gmail.com"', html=False)
        self.assertContains(response, 'href="/privacy/"', html=False)

    def test_expired_inquiry_cleanup_is_dry_run_by_default_and_preserves_orders(self):
        old = timezone.now() - timedelta(days=366)
        recent = timezone.now() - timedelta(days=364)
        expired = CustomOrderInquiry.objects.create(
            name="Expired Request",
            email="expired@example.com",
            request_details="A request that was never accepted.",
        )
        declined = CustomOrderInquiry.objects.create(
            name="Declined Request",
            email="declined@example.com",
            request_details="A declined request.",
            status=CustomOrderInquiry.Status.DECLINED,
        )
        active = CustomOrderInquiry.objects.create(
            name="Recent Request",
            email="recent@example.com",
            request_details="A recent request.",
        )
        accepted = CustomOrderInquiry.objects.create(
            name="Accepted Request",
            email="accepted@example.com",
            request_details="An accepted request.",
            status=CustomOrderInquiry.Status.ACCEPTED,
        )
        converted = CustomOrderInquiry.objects.create(
            name="Converted Request",
            email="converted@example.com",
            request_details="A converted request.",
            status=CustomOrderInquiry.Status.CONVERTED,
        )
        CustomOrderInquiry.objects.filter(pk__in=[expired.pk, declined.pk]).update(
            updated_at=old
        )
        CustomOrderInquiry.objects.filter(
            pk__in=[active.pk, accepted.pk, converted.pk]
        ).update(updated_at=recent)
        CustomOrderInquiry.objects.filter(
            pk__in=[accepted.pk, converted.pk]
        ).update(updated_at=old)

        dry_run_output = StringIO()
        call_command("purge_expired_inquiries", stdout=dry_run_output)

        self.assertIn("2 eligible for deletion", dry_run_output.getvalue())
        self.assertTrue(CustomOrderInquiry.objects.filter(pk=expired.pk).exists())
        self.assertTrue(CustomOrderInquiry.objects.filter(pk=declined.pk).exists())

        execute_output = StringIO()
        call_command("purge_expired_inquiries", "--execute", stdout=execute_output)

        self.assertIn("2 deleted", execute_output.getvalue())
        self.assertFalse(CustomOrderInquiry.objects.filter(pk=expired.pk).exists())
        self.assertFalse(CustomOrderInquiry.objects.filter(pk=declined.pk).exists())
        self.assertTrue(CustomOrderInquiry.objects.filter(pk=active.pk).exists())
        self.assertTrue(CustomOrderInquiry.objects.filter(pk=accepted.pk).exists())
        self.assertTrue(CustomOrderInquiry.objects.filter(pk=converted.pk).exists())

    def test_homepage_has_branded_search_metadata_and_optional_verification(self):
        with override_settings(
            DEBUG=False,
            PUBLIC_SITE_URL="https://grannycoded.example",
            GOOGLE_SITE_VERIFICATION="sample-verification-token",
        ):
            response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "<title>GrannyCoded | One-of-a-kind quilt clothing</title>",
            html=False,
        )
        self.assertContains(
            response,
            '<link rel="canonical" href="https://grannycoded.example/">',
            html=False,
        )
        self.assertContains(
            response,
            'name="google-site-verification" content="sample-verification-token"',
            html=False,
        )
        self.assertContains(response, 'name="robots" content="index,follow"', html=False)
        self.assertNotContains(response, "Welcome to your new Wagtail site")
        structured_data = (
            response.content.decode()
            .split('<script type="application/ld+json">', 1)[1]
            .split("</script>", 1)[0]
        )
        self.assertEqual(json.loads(structured_data)["@graph"][1]["@type"], "WebSite")

    def test_sitemap_includes_live_products_but_not_draft_products(self):
        public_product = self.create_product()
        draft_product = self.create_product(
            slug="unpublished-product",
            title="Unpublished Product",
            is_public=False,
        )

        response = self.client.get("/sitemap.xml")

        self.assertEqual(response.status_code, 200)
        self.assertIn("application/xml", response["Content-Type"])
        root = ElementTree.fromstring(response.content)
        namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
        locations = {
            entry.text
            for entry in root.findall(f"{namespace}url/{namespace}loc")
        }
        self.assertIn(f"{settings.PUBLIC_SITE_URL}/", locations)
        self.assertIn(f"{settings.PUBLIC_SITE_URL}/shop/", locations)
        self.assertIn(f"{settings.PUBLIC_SITE_URL}/custom-order/", locations)
        self.assertIn(f"{settings.PUBLIC_SITE_URL}/shipping-returns/", locations)
        self.assertIn(f"{settings.PUBLIC_SITE_URL}/privacy/", locations)
        self.assertIn(
            f"{settings.PUBLIC_SITE_URL}{public_product.get_absolute_url()}",
            locations,
        )
        self.assertNotIn(
            f"{settings.PUBLIC_SITE_URL}{draft_product.get_absolute_url()}",
            locations,
        )

    def test_robots_disallows_local_crawling_and_advertises_production_sitemap(self):
        with override_settings(DEBUG=True):
            local_response = self.client.get("/robots.txt")
        self.assertEqual(local_response.status_code, 200)
        self.assertContains(local_response, "Disallow: /")

        with override_settings(
            DEBUG=False,
            PUBLIC_SITE_URL="https://grannycoded.example",
        ):
            production_response = self.client.get("/robots.txt")

        self.assertContains(production_response, "Disallow: /admin/")
        self.assertContains(production_response, "Allow: /")
        self.assertContains(
            production_response,
            "Sitemap: https://grannycoded.example/sitemap.xml",
        )

    def test_oscar_catalogue_and_product_detail_use_the_brand_templates(self):
        product = self.create_product()

        shop_response = self.client.get(reverse("catalogue:index"))
        self.assertEqual(shop_response.status_code, 200)
        self.assertContains(shop_response, product.title)
        self.assertContains(shop_response, "$179.00")
        self.assertContains(shop_response, "One of a kind · available")

        detail_response = self.client.get(product.get_absolute_url())
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, product.title)
        self.assertContains(detail_response, 'type="number"', html=False)
        self.assertContains(detail_response, "Add to cart")

    def test_category_and_search_browse_filter_oscar_products(self):
        product = self.create_product()

        category_response = self.client.get(self.category.get_absolute_url())
        search_response = self.client.get(reverse("catalogue:index"), {"q": "Mimi"})

        self.assertContains(category_response, product.title)
        self.assertContains(search_response, product.title)

    def test_sold_one_off_remains_visible_but_cannot_be_added_to_basket(self):
        product = self.create_product(stock=0)

        shop_response = self.client.get(reverse("catalogue:index"))
        detail_response = self.client.get(product.get_absolute_url())

        self.assertContains(shop_response, "Sold")
        self.assertContains(detail_response, "This piece has sold.")
        self.assertNotContains(detail_response, "Add to cart")
        self.assertContains(detail_response, "Ask about custom work")

    def test_deleting_a_product_image_queues_delayed_object_cleanup(self):
        product = self.create_product()
        object_name = "products/2026/10/01ARZ3NDEKTSV4RRFFQ69G5FAV.webp"
        image = self.ProductImage.objects.create(
            product=product,
            code="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            original=object_name,
            caption=product.title,
        )

        image.delete()

        pending = PendingImageDeletion.objects.get(
            storage_alias="default",
            object_name=object_name,
        )
        self.assertGreater(pending.delete_after, timezone.now())

    def test_cleanup_retains_objects_referenced_by_thumbnail_cache(self):
        source = Source.objects.create(
            storage_hash="source-storage-hash",
            name="products/source-image.webp",
        )
        Thumbnail.objects.create(
            storage_hash="thumbnail-storage-hash",
            name="products/cached-derivative.jpg",
            source=source,
        )

        self.assertTrue(
            PurgePendingImages._file_is_referenced(
                "default",
                "products/cached-derivative.jpg",
            )
        )

    def test_product_description_is_html_escaped(self):
        product = self.create_product()
        product.description = '<script>alert("x")</script>'
        product.save()

        response = self.client.get(product.get_absolute_url())

        self.assertContains(response, "&lt;script&gt;")
        # The page legitimately contains the tag manager <script>, so assert on
        # the injected payload rather than on the tag itself.
        self.assertNotContains(response, "<script>alert(&quot;x&quot;)", html=False)

    def test_variant_stock_and_price_are_managed_on_each_child_product(self):
        parent = self.Product.objects.create(
            title="Quilted Market Bag",
            slug="quilted-market-bag",
            structure=self.Product.PARENT,
            product_class=self.product_class,
            is_public=True,
        )
        parent.categories.add(self.category)
        variant = self.Product.objects.create(
            title="Large",
            slug="quilted-market-bag-large",
            structure=self.Product.CHILD,
            parent=parent,
            is_public=True,
        )
        self.StockRecord.objects.create(
            product=variant,
            partner=self.partner,
            partner_sku="quilted-market-bag-large",
            price_currency="USD",
            price=Decimal("55.00"),
            num_in_stock=3,
            num_allocated=0,
        )

        parent_response = self.client.get(parent.get_absolute_url())
        variant_response = self.client.get(variant.get_absolute_url())

        self.assertContains(parent_response, "Choose a version")
        self.assertContains(parent_response, variant.get_absolute_url())
        self.assertContains(variant_response, "Large")
        self.assertContains(variant_response, "$55.00")
        self.assertContains(variant_response, 'type="number"', html=False)
        self.assertContains(variant_response, "Add to cart")
        self.assertNotContains(variant_response, "Shipping and returns details")

        self.client.post(
            reverse("basket:add", kwargs={"pk": variant.pk}),
            {"quantity": 1, "next": variant.get_absolute_url()},
            HTTP_REFERER=variant.get_absolute_url(),
        )
        basket = self.client.get(reverse("basket:summary")).wsgi_request.basket
        self.assertEqual(basket.lines.get().product, variant)

    @override_settings(STRIPE_ENABLED=False, STRIPE_SECRET_KEY="")
    def test_basket_leads_to_checkout_and_checkout_closes_without_stripe(self):
        product = self.create_product()
        add_response = self.client.post(
            reverse("basket:add", kwargs={"pk": product.pk}),
            {"quantity": 1, "next": product.get_absolute_url()},
            HTTP_REFERER=product.get_absolute_url(),
        )

        self.assertEqual(add_response.status_code, 302)
        basket_response = self.client.get(reverse("basket:summary"))
        self.assertEqual(basket_response.status_code, 200)
        self.assertContains(basket_response, product.title)
        self.assertContains(basket_response, "Cart (")
        self.assertContains(basket_response, "Your cart")
        self.assertContains(basket_response, "added to your cart")
        self.assertContains(basket_response, "Review order")
        self.assertNotContains(basket_response, "Review shipping and returns")

        checkout_response = self.client.get(reverse("checkout:index"))
        self.assertEqual(checkout_response.status_code, 200)
        self.assertContains(checkout_response, "Online checkout is opening soon.")
        self.assertContains(checkout_response, "Your cart is still here.")
        self.assertContains(checkout_response, "Return to your cart")
        self.assertNotContains(checkout_response, "Review shipping and returns")

    def test_blog_pages_render_editorial_content_and_old_slug_redirects(self):
        self.assertNotContains(self.client.get("/"), 'href="/blog/"')
        blog = self.home.add_child(
            instance=BlogIndexPage(
                title="Journal",
                slug="journal",
                intro="Stories about found quilts and one-of-a-kind pieces.",
            )
        )
        blog.save_revision().publish()
        blog.title = "Blog"
        blog.slug = "blog"
        blog.save_revision().publish()
        Redirect.add_redirect(
            "/journal/",
            redirect_to="/blog/",
            site=Site.objects.get(is_default_site=True),
        )

        cover = ImageAsset.objects.create(
            display_name="A found quilt",
            original_name="found-quilt.webp",
            category=ImageAsset.Category.EDITORIAL,
            visibility=ImageAsset.Visibility.PUBLIC,
            public_file="editorial/01ARZ3NDEKTSV4RRFFQ69G5FAV.webp",
            content_type="image/webp",
            status=ImageAsset.Status.ACTIVE,
        )
        old_url_response = self.client.get("/journal/")
        self.assertEqual(old_url_response.status_code, 301)
        self.assertEqual(old_url_response.url, "/blog/")

        post = blog.add_child(
            instance=BlogPostPage(
                title="A Quilt Finds a New Life",
                slug="quilt-new-life",
                excerpt="A short note about remaking textiles.",
                cover_asset=cover,
            )
        )
        post.save_revision().publish()

        blog_response = self.client.get("/blog/")
        post_response = self.client.get("/blog/quilt-new-life/")

        self.assertEqual(blog_response.status_code, 200)
        self.assertContains(blog_response, post.title)
        self.assertEqual(post_response.status_code, 200)
        self.assertContains(post_response, post.excerpt)
        self.assertContains(
            post_response,
            f'<img class="article-cover" src="{cover.get_url()}"',
            html=False,
        )
        home_response = self.client.get("/")
        self.assertContains(home_response, 'href="/blog/"')
        self.assertContains(home_response, "Visit the blog")

    def test_blog_posts_admin_menu_opens_the_post_list(self):
        blog = self.home.add_child(
            instance=BlogIndexPage(title="Blog", slug="blog")
        )
        user = get_user_model().objects.create_user(
            username="blog-editor",
            password="test-password",
            is_staff=True,
        )
        request = RequestFactory().get("/admin/")
        request.user = user

        menu_item = BlogPostsMenuItem()

        self.assertTrue(menu_item.is_shown(request))
        self.assertEqual(
            menu_item.url,
            reverse("wagtailadmin_explore", args=[blog.pk]),
        )

        request.user.is_staff = False
        self.assertFalse(menu_item.is_shown(request))

    def test_blog_post_editor_exposes_named_editing_fields(self):
        blog = self.home.add_child(
            instance=BlogIndexPage(title="Blog", slug="blog")
        )
        cover = ImageAsset.objects.create(
            display_name="Current quilt cover",
            original_name="current-cover.jpg",
            category=ImageAsset.Category.EDITORIAL,
            visibility=ImageAsset.Visibility.PUBLIC,
            public_file=f"editorial/{new_ulid()}.jpg",
            content_type="image/jpeg",
            status=ImageAsset.Status.ACTIVE,
        )
        post = blog.add_child(
            instance=BlogPostPage(
                title="A New Life for Found Quilts",
                slug="a-new-life-for-found-quilts",
                cover_asset=cover,
            )
        )
        user = get_user_model().objects.create_superuser(
            username="blog-admin",
            email="blog-admin@example.com",
            password="test-password",
        )
        self.client.force_login(user)

        response = self.client.get(
            reverse("wagtailadmin_pages:edit", args=[post.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Post title")
        self.assertContains(response, "Short summary")
        self.assertContains(response, "Post body")
        self.assertContains(response, "Tags")
        self.assertContains(response, "Upload a cover image")
        self.assertContains(response, 'name="cover_upload"')
        self.assertContains(response, 'type="file"')
        self.assertContains(response, 'accept=".jpg,.jpeg,.png,.webp,.avif"')
        self.assertContains(response, "grannycoded-cover-upload")
        self.assertContains(response, "up to 20 MB")
        self.assertContains(response, "Current cover: Current quilt cover.")
        self.assertNotContains(response, 'name="cover_asset"')
        self.assertContains(response, "Blog posts")
        self.assertContains(
            response,
            reverse("wagtailadmin_explore", args=[blog.pk]),
        )

        post_list = self.client.get(
            reverse("wagtailadmin_explore", args=[blog.pk])
        )
        self.assertEqual(post_list.status_code, 200)
        self.assertContains(post_list, post.title)
        self.assertContains(
            post_list,
            reverse("wagtailadmin_pages:add_subpage", args=[blog.pk]),
        )

    def test_blog_post_upload_creates_and_links_public_editorial_asset(self):
        blog = self.home.add_child(
            instance=BlogIndexPage(title="Blog", slug="blog")
        )
        current_cover = ImageAsset.objects.create(
            display_name="Older cover",
            original_name="older-cover.jpg",
            category=ImageAsset.Category.EDITORIAL,
            visibility=ImageAsset.Visibility.PUBLIC,
            public_file=f"editorial/{new_ulid()}.jpg",
            content_type="image/jpeg",
            status=ImageAsset.Status.ACTIVE,
        )
        post = blog.add_child(
            instance=BlogPostPage(
                title="A New Life for Found Quilts",
                slug="a-new-life-for-found-quilts",
                cover_asset=current_cover,
            )
        )
        user = get_user_model().objects.create_superuser(
            username="cover-uploader",
            email="cover-uploader@example.com",
            password="test-password",
        )
        image_bytes = BytesIO()
        Image.new("RGB", (4, 4), color="olive").save(image_bytes, format="JPEG")
        uploaded_image = SimpleUploadedFile(
            "found-quilt.jpg",
            image_bytes.getvalue(),
            content_type="image/jpeg",
        )
        form_class = BlogPostPage.get_edit_handler().get_form_class()
        form = form_class(
            data={
                "title": post.title,
                "slug": post.slug,
                "excerpt": "A story about a found quilt.",
            },
            files={"cover_upload": uploaded_image},
            instance=post,
            parent_page=blog,
            for_user=user,
        )
        self.assertTrue(form.is_valid(), form.errors)

        with TemporaryDirectory() as storage_dir, override_settings(
            STORAGES={
                **settings.STORAGES,
                "public_images": {
                    "BACKEND": "django.core.files.storage.FileSystemStorage",
                    "OPTIONS": {"location": storage_dir},
                },
            }
        ):
            saved_post = form.save()
            asset = saved_post.cover_asset
            saved_post.refresh_from_db()

            self.assertEqual(saved_post.cover_asset_id, asset.pk)
            self.assertEqual(asset.category, ImageAsset.Category.EDITORIAL)
            self.assertEqual(asset.visibility, ImageAsset.Visibility.PUBLIC)
            self.assertEqual(asset.status, ImageAsset.Status.ACTIVE)
            self.assertEqual(asset.original_name, "found-quilt.jpg")
            self.assertEqual(len(asset.sha256), 64)
            self.assertTrue(Path(storage_dir, asset.public_file.name).is_file())
            current_cover.refresh_from_db()
            self.assertEqual(
                current_cover.status,
                ImageAsset.Status.DELETION_PENDING,
            )

    def test_blog_post_upload_rejects_invalid_image_content(self):
        blog = self.home.add_child(
            instance=BlogIndexPage(title="Blog", slug="blog")
        )
        post = blog.add_child(
            instance=BlogPostPage(
                title="A New Life for Found Quilts",
                slug="a-new-life-for-found-quilts",
            )
        )
        user = get_user_model().objects.create_superuser(
            username="invalid-cover-uploader",
            email="invalid-cover@example.com",
            password="test-password",
        )
        form_class = BlogPostPage.get_edit_handler().get_form_class()
        form = form_class(
            data={"title": post.title, "slug": post.slug},
            files={
                "cover_upload": SimpleUploadedFile(
                    "not-an-image.jpg",
                    b"not an image",
                    content_type="image/jpeg",
                )
            },
            instance=post,
            parent_page=blog,
            for_user=user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("cover_upload", form.errors)
        self.assertFalse(ImageAsset.objects.exists())

    def test_blog_index_has_an_empty_state_and_paginates_larger_archives(self):
        blog = self.home.add_child(
            instance=BlogIndexPage(
                title="Blog",
                slug="blog",
                intro="Stories about found quilts.",
            )
        )
        blog.save_revision().publish()

        empty_response = self.client.get("/blog/")
        self.assertContains(empty_response, "The first story is taking shape.")

        for index in range(11):
            post = blog.add_child(
                instance=BlogPostPage(
                    title=f"Quilt story {index + 1}",
                    slug=f"quilt-story-{index + 1}",
                    excerpt="A short note about a found textile.",
                )
            )
            post.save_revision().publish()

        first_page = self.client.get("/blog/")
        second_page = self.client.get("/blog/", {"page": 2})

        self.assertContains(first_page, "Page 1 of 2")
        self.assertContains(first_page, "More stories")
        self.assertContains(second_page, "Page 2 of 2")
        self.assertContains(second_page, "Quilt story 1")

    def test_blog_tags_are_displayed_without_filtering_posts(self):
        blog = self.home.add_child(
            instance=BlogIndexPage(title="Blog", slug="blog")
        )
        tagged_post = blog.add_child(
            instance=BlogPostPage(
                title="A Found Quilt",
                slug="a-found-quilt",
                excerpt="A story about a found quilt.",
            )
        )
        tagged_post.tags.add("Found quilts")
        tagged_post.save_revision().publish()

        other_post = blog.add_child(
            instance=BlogPostPage(
                title="A Custom Piece",
                slug="a-custom-piece",
                excerpt="A custom-work story.",
            )
        )
        other_post.tags.add("Custom work")
        other_post.save_revision().publish()

        blog_response = self.client.get("/blog/", {"tag": "found-quilts"})
        article_response = self.client.get("/blog/a-found-quilt/")

        self.assertEqual(blog_response.status_code, 200)
        self.assertContains(blog_response, "A Found Quilt")
        self.assertContains(blog_response, "A Custom Piece")
        self.assertContains(blog_response, "Found quilts")
        self.assertNotContains(blog_response, "Browse by topic")
        self.assertNotContains(blog_response, 'href="?tag=')
        self.assertContains(article_response, "Found quilts")
        self.assertNotContains(article_response, "/blog/?tag=")

    def test_custom_order_request_is_saved_for_wagtail_review(self):
        response = self.client.post(
            reverse("custom_order_request"),
            {
                "name": "Taylor Shopper",
                "email": "taylor@example.com",
                "request_details": "I would love a quilt coat with deep pockets.",
            },
        )

        self.assertEqual(response.status_code, 302)
        inquiry = CustomOrderInquiry.objects.get()
        self.assertEqual(inquiry.name, "Taylor Shopper")
        self.assertEqual(inquiry.status, CustomOrderInquiry.Status.NEW)
        form_response = self.client.get(reverse("custom_order_request"))
        self.assertContains(form_response, "Custom work")
        self.assertNotContains(form_response, "custom-order cancellation terms")
        self.assertContains(form_response, "privacy notice")

    def test_custom_order_request_accepts_an_optional_reference_photo(self):
        image_bytes = BytesIO()
        Image.new("RGB", (2, 2), color="olive").save(image_bytes, format="JPEG")
        photo = SimpleUploadedFile(
            "reference.jpg",
            image_bytes.getvalue(),
            content_type="image/jpeg",
        )
        with TemporaryDirectory() as media_dir, override_settings(MEDIA_ROOT=media_dir):
            response = self.client.post(
                reverse("custom_order_request"),
                {
                    "name": "Taylor Shopper",
                    "email": "taylor@example.com",
                    "request_details": "A coat inspired by this reference.",
                    "reference_upload": photo,
                },
            )
            inquiry = CustomOrderInquiry.objects.get()
            asset = inquiry.reference_asset
            self.assertIsNotNone(asset)
            self.assertRegex(asset.pk, r"^[0-9A-HJKMNP-TV-Z]{26}$")
            self.assertTrue(asset.private_file.name.endswith(f"{asset.pk}.jpg"))
            self.assertEqual(asset.display_name, "reference.jpg")

            private_url = reverse("private_image_asset", kwargs={"asset_id": asset.pk})
            self.assertEqual(self.client.get(private_url).status_code, 302)
            staff = get_user_model().objects.create_superuser(
                username="photo-reviewer",
                email="photo-reviewer@example.com",
                password="test-password",
            )
            self.client.force_login(staff)
            private_response = self.client.get(private_url)
            self.assertEqual(private_response.status_code, 200)
            self.assertEqual(private_response["Cache-Control"], "private, no-store")
            self.assertEqual(
                b"".join(private_response.streaming_content),
                image_bytes.getvalue(),
            )

            inquiry.delete()
            asset.refresh_from_db()
            self.assertEqual(asset.status, ImageAsset.Status.DELETION_PENDING)
            self.assertGreater(asset.purge_after, timezone.now())

        self.assertEqual(response.status_code, 302)

    def test_accepted_custom_quote_creates_a_private_pending_oscar_order(self):
        inquiry = CustomOrderInquiry.objects.create(
            name="Taylor Shopper",
            email="taylor@example.com",
            request_details="A custom quilt coat with deep pockets.",
            status=CustomOrderInquiry.Status.NEW,
        )
        staff = get_user_model().objects.create_superuser(
            username="leah",
            email="leah@example.com",
            password="test-password",
        )
        self.client.force_login(staff)

        quote_response = self.client.post(
            reverse("custom_order_detail", kwargs={"inquiry_id": inquiry.pk}),
            {
                "status": CustomOrderInquiry.Status.ACCEPTED,
                "quoted_total": "150.00",
                "quoted_shipping": "10.00",
                "shipping_note": "U.S. shipping included in the agreed total.",
                "maker_notes": "Use the floral quilt Leah selected.",
            },
        )
        self.assertEqual(quote_response.status_code, 302)

        convert_response = self.client.post(
            reverse("convert_custom_order", kwargs={"inquiry_id": inquiry.pk})
        )

        self.assertEqual(convert_response.status_code, 302)
        inquiry.refresh_from_db()
        order = get_model("order", "Order").objects.get()
        line = order.lines.get()
        stockrecord = self.StockRecord.objects.get(pk=line.stockrecord_id)
        self.assertEqual(inquiry.status, CustomOrderInquiry.Status.CONVERTED)
        self.assertEqual(inquiry.order, order)
        self.assertEqual(order.status, "Pending")
        self.assertEqual(order.guest_email, "taylor@example.com")
        self.assertEqual(order.total_incl_tax, Decimal("150.00"))
        self.assertEqual(stockrecord.num_allocated, 1)
        self.assertFalse(order.lines.get().product.is_public)

    def test_in_person_custom_order_can_be_recorded_after_quote_acceptance(self):
        staff = get_user_model().objects.create_superuser(
            username="custom-maker",
            email="leah@example.com",
            password="test-password",
        )
        self.client.force_login(staff)

        response = self.client.post(
            reverse("create_in_person_custom_order"),
            {
                "name": "Jordan Shopper",
                "email": "jordan@example.com",
                "request_details": "A quilt coat with two deep pockets.",
                "quoted_total": "150.00",
                "quoted_shipping": "0.00",
                "shipping_note": "Pickup at the craft fair.",
                "maker_notes": "Customer accepted the quote in person.",
            },
        )

        self.assertEqual(response.status_code, 302)
        inquiry = CustomOrderInquiry.objects.get()
        order = inquiry.order
        self.assertEqual(inquiry.status, CustomOrderInquiry.Status.CONVERTED)
        self.assertIsNotNone(order)
        self.assertEqual(order.status, "Pending")
        self.assertEqual(order.guest_email, "jordan@example.com")
        self.assertEqual(order.total_incl_tax, Decimal("150.00"))

    def test_in_person_sale_records_paid_order_and_consumes_unpublished_stock(self):
        product = self.create_product(stock=1, is_public=False)
        staff = get_user_model().objects.create_superuser(
            username="market-maker",
            email="leah@example.com",
            password="test-password",
        )
        self.client.force_login(staff)

        response = self.client.post(
            reverse("record_manual_sale"),
            {
                "payment_method": "cash",
                "customer_email": "",
                "notes": "Saturday craft fair",
                "sale-lines-TOTAL_FORMS": "1",
                "sale-lines-INITIAL_FORMS": "0",
                "sale-lines-MIN_NUM_FORMS": "1",
                "sale-lines-MAX_NUM_FORMS": "10",
                "sale-lines-0-product": str(product.pk),
                "sale-lines-0-quantity": "1",
            },
        )

        self.assertEqual(response.status_code, 302)
        order = get_model("order", "Order").objects.get()
        line = order.lines.get()
        stockrecord = self.StockRecord.objects.get(product=product)
        self.assertEqual(order.status, "Complete")
        self.assertEqual(order.guest_email, "")
        self.assertEqual(order.payment_events.get().event_type.code, "paid")
        self.assertEqual(order.shipping_events.get().event_type.code, "collected")
        self.assertEqual(stockrecord.num_in_stock, 0)
        self.assertEqual(stockrecord.num_allocated, 0)
        self.assertEqual(line.status, "Complete")

    def test_oscar_shop_tools_require_a_staff_user(self):
        response = self.client.get(reverse("record_manual_sale"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/dashboard/login/", response.url)

    def test_wagtail_admin_home_loads_for_staff(self):
        asset = ImageAsset.objects.create(
            display_name="GrannyCoded logo",
            original_name="logo.avif",
            category=ImageAsset.Category.BRAND,
            visibility=ImageAsset.Visibility.PUBLIC,
            public_file="brand/test-wagtail-logo.avif",
            content_type="image/avif",
            status=ImageAsset.Status.ACTIVE,
        )
        BrandSettings.objects.update_or_create(
            site=Site.objects.get(is_default_site=True),
            defaults={"logo_asset": asset},
        )
        staff = get_user_model().objects.create_superuser(
            username="wagtail-admin",
            email="admin@example.com",
            password="test-password",
        )
        self.client.force_login(staff)

        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard - GrannyCoded")
        self.assertContains(response, asset.get_url())
        self.assertContains(response, "grannycoded-admin-logo")
        self.assertContains(response, "css/wagtail-admin-branding.css")

    def test_oscar_dashboard_exposes_grannycoded_shop_tools_to_staff(self):
        staff = get_user_model().objects.create_superuser(
            username="shop-manager",
            email="manager@example.com",
            password="test-password",
        )
        self.client.force_login(staff)

        home_response = self.client.get("/")
        self.assertNotContains(home_response, "Record a sale")
        self.assertNotContains(home_response, "Custom orders")

        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Custom orders")
        self.assertContains(response, "Record in-person sale")

        catalogue_response = self.client.get(reverse("dashboard:catalogue-product-list"))
        self.assertEqual(catalogue_response.status_code, 200)
        self.assertContains(catalogue_response, "Products")

    def test_oscar_dashboard_uses_the_grannycoded_logo_as_its_favicon(self):
        asset = ImageAsset.objects.create(
            display_name="GrannyCoded logo",
            original_name="logo.avif",
            category=ImageAsset.Category.BRAND,
            visibility=ImageAsset.Visibility.PUBLIC,
            public_file="brand/test-logo.avif",
            content_type="image/avif",
            status=ImageAsset.Status.ACTIVE,
        )
        BrandSettings.objects.update_or_create(
            site=Site.objects.get(is_default_site=True),
            defaults={"logo_asset": asset},
        )
        staff = get_user_model().objects.create_superuser(
            username="dashboard-logo-reviewer",
            email="dashboard-logo@example.com",
            password="test-password",
        )
        self.client.force_login(staff)

        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'<link rel="icon" href="{asset.get_url()}" type="image/avif">',
            html=False,
        )
        self.assertContains(
            response,
            f'background-image: url("{asset.get_url()}");',
            html=False,
        )
        self.assertNotContains(response, 'href="/static/oscar/favicon.ico"')
        self.assertNotContains(response, "logo_oscar.png")

    def test_catalog_import_creates_private_zero_stock_oscar_drafts_idempotently(self):
        manifest = {
            "version": 1,
            "products": {
                "4602600325": {
                    "ulid": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                    "storage_name": "products/01ARZ3NDEKTSV4RRFFQ69G5FAV.webp",
                    "display_name": "Floral Duster Coat",
                    "alt_text": "Floral Duster Coat",
                }
            },
            "logo": None,
        }
        with TemporaryDirectory() as directory:
            manifest_path = Path(directory) / "catalog_image_manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            call_command("import_granny_catalog", "--image-manifest", manifest_path)
            call_command("import_granny_catalog", "--image-manifest", manifest_path)

        product = self.Product.objects.get(slug="floral-duster-coat-vintage-tablecloth")
        stockrecord = self.StockRecord.objects.get(product=product)
        self.assertEqual(self.Product.objects.count(), 12)
        self.assertFalse(product.is_public)
        self.assertEqual(product.priority, 1)
        self.assertEqual(stockrecord.num_in_stock, 0)
        self.assertEqual(stockrecord.price, Decimal("95.00"))
        image = ProductImageAsset.objects.select_related("asset").get(product=product)
        image_details = manifest["products"]["4602600325"]
        self.assertEqual(image.asset.pk, image_details["ulid"])
        self.assertEqual(image.asset.public_file.name, image_details["storage_name"])
        self.assertEqual(image.asset.display_name, "Floral Duster Coat")
        self.assertEqual(image.alt_text, "Floral Duster Coat")


class HealthCheckTests(TestCase):
    def test_health_reports_ready(self):
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_health_is_reachable_over_plain_http_behind_the_proxy(self):
        response = self.client.get("/health/", secure=False)

        self.assertEqual(response.status_code, 200)

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_public_pages_still_redirect_to_https(self):
        response = self.client.get("/shop/", secure=False)

        self.assertEqual(response.status_code, 301)
        self.assertTrue(response["Location"].startswith("https://"))


class SetSiteDomainCommandTests(TestCase):
    def test_command_points_both_site_records_at_the_domain(self):
        call_command("set_site_domain", "grannycoded.example", "--site-name", "GrannyCoded")

        wagtail_site = Site.objects.get(is_default_site=True)
        self.assertEqual(wagtail_site.hostname, "grannycoded.example")
        self.assertEqual(wagtail_site.port, 443)

        django_site = DjangoSite.objects.get(pk=settings.SITE_ID)
        self.assertEqual(django_site.domain, "grannycoded.example")
        self.assertEqual(django_site.name, "GrannyCoded")

    def test_command_rejects_a_full_url(self):
        with self.assertRaises(CommandError):
            call_command("set_site_domain", "https://grannycoded.example/")
