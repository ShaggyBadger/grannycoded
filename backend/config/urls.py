from django.apps import apps
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

from home import views as home_views
from home import ops_views
from home import seo as seo_views

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("robots.txt", seo_views.robots_txt, name="robots_txt"),
    path("sitemap.xml", seo_views.sitemap_xml, name="sitemap_xml"),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("shop/", include("home.catalogue_urls")),
    path("basket/", apps.get_app_config("basket").urls),
    path("accounts/", apps.get_app_config("customer").urls),
    path("checkout/", include("home.checkout_urls")),
    path("dashboard/custom-orders/", ops_views.custom_order_queue, name="custom_order_queue"),
    path("dashboard/custom-orders/new/", ops_views.create_in_person_custom_order, name="create_in_person_custom_order"),
    path("dashboard/custom-orders/<int:inquiry_id>/convert/", ops_views.convert_custom_order, name="convert_custom_order"),
    path("dashboard/custom-orders/<int:inquiry_id>/reference-photo/", ops_views.custom_order_reference_photo, name="custom_order_reference_photo"),
    path("dashboard/image-assets/private/<str:asset_id>/", ops_views.private_image_asset, name="private_image_asset"),
    path("dashboard/custom-orders/<int:inquiry_id>/", ops_views.custom_order_detail, name="custom_order_detail"),
    path("dashboard/record-sale/", ops_views.record_manual_sale, name="record_manual_sale"),
    path("dashboard/", apps.get_app_config("dashboard").urls),
    path("custom-order/", home_views.custom_order_request, name="custom_order_request"),
    path("", include(wagtail_urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
