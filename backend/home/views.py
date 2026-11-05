"""Public custom-order inquiry and disabled checkout views."""

import logging
from smtplib import SMTPException

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Q
from django.http import HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET
from django.views.generic import ListView
from oscar.core.loading import get_class, get_model

from home.forms import CustomOrderInquiryForm

logger = logging.getLogger(__name__)


class OscarCatalogueView(ListView):
    """Database-backed catalogue listing using Oscar's public products."""

    template_name = "oscar/catalogue/browse.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        Product = get_model("catalogue", "Product")
        queryset = self.product_queryset(Product)
        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            )
        return queryset

    def product_queryset(self, Product):
        return (
            Product.objects.browsable()
            .exclude(structure=Product.CHILD)
            .select_related("product_class")
            .prefetch_related(
                "categories",
                "images",
                "managed_images__asset",
                "stockrecords",
                "children__stockrecords",
            )
            .order_by("-priority", "-date_created")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        Category = get_model("catalogue", "Category")
        root = Category.get_root_nodes().filter(slug="shop").first()
        context["shop_categories"] = root.get_children().browsable() if root else []
        active_category = getattr(self, "category", None) or root
        context["shop_intro"] = (
            active_category.description
            if active_category and active_category.description
            else "Finished pieces are listed as they become available."
        )
        context["search_query"] = self.request.GET.get("q", "")
        context["summary"] = active_category.name if getattr(self, "category", None) else "Shop the pieces"
        return context


class OscarCategoryView(OscarCatalogueView):
    def dispatch(self, request, *args, **kwargs):
        Category = get_model("catalogue", "Category")
        self.category = get_object_or_404(
            Category.objects.browsable(),
            pk=kwargs["pk"],
        )
        if self.category.full_slug != kwargs["category_slug"]:
            return HttpResponsePermanentRedirect(self.category.get_absolute_url())
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        Product = get_model("catalogue", "Product")
        category_tree = self.category.get_descendants_and_self()
        queryset = self.product_queryset(Product).filter(
            categories__in=category_tree
        ).distinct()
        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            )
        return queryset


OscarProductDetailView = get_class("catalogue.views", "ProductDetailView")


class ProductDetailView(OscarProductDetailView):
    def get_queryset(self):
        return super().get_queryset().prefetch_related("images", "managed_images__asset")


def custom_order_request(request):
    if request.method == "POST":
        form = CustomOrderInquiryForm(request.POST, request.FILES)
        if form.is_valid():
            inquiry = form.save()
            recipient = settings.CUSTOM_ORDER_NOTIFICATION_EMAIL
            if recipient and settings.EMAIL_HOST:
                try:
                    send_mail(
                        subject=f"New GrannyCoded custom-order inquiry #{inquiry.pk}",
                        message=(
                            f"From: {inquiry.name}\n"
                            f"Email: {inquiry.email}\n\n"
                            f"Request:\n{inquiry.request_details}"
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[recipient],
                        fail_silently=False,
                    )
                except (SMTPException, OSError):
                    logger.exception(
                        "Custom-order notification failed; inquiry_id=%s", inquiry.pk
                    )
                    messages.warning(
                        request,
                        "Your request was saved, but its email notification could not "
                        "be sent. Leah can still review it in the site admin.",
                    )
                    return redirect("custom_order_request")
            elif recipient:
                messages.warning(
                    request,
                    "Your request was saved, but email delivery is not configured. "
                    "Leah can review it in the Oscar shop tools.",
                )
                return redirect("custom_order_request")
            messages.success(
                request,
                "Thanks for sharing your idea. Leah will review your request and "
                "follow up with a quote.",
            )
            return redirect("custom_order_request")
    else:
        form = CustomOrderInquiryForm()

    return render(request, "home/custom_order_request.html", {"form": form})


@require_GET
def checkout_unavailable(request):
    """Explain why checkout is closed when Stripe is not configured."""
    return render(request, "home/checkout_unavailable.html", status=200)
