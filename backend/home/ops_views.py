"""Staff workflows that extend Oscar's standard order dashboard."""

import mimetypes

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from django.core.files.storage import storages
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from home.forms import (
    CustomOrderCreateForm,
    CustomOrderQuoteForm,
    ManualSaleForm,
    ManualSaleLineFormSet,
)
from home.models import CustomOrderInquiry, ImageAsset
from home.services.oscar_orders import (
    InventoryUnavailable,
    create_oscar_order,
    create_order_for_custom_inquiry,
)


@staff_member_required(login_url="/dashboard/login/")
def custom_order_queue(request):
    inquiries = CustomOrderInquiry.objects.select_related("order").all()
    return render(
        request,
        "home/dashboard/custom_order_queue.html",
        {"inquiries": inquiries},
    )


@staff_member_required(login_url="/dashboard/login/")
@require_http_methods(["GET", "POST"])
@transaction.atomic
def create_in_person_custom_order(request):
    form = CustomOrderCreateForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        inquiry = form.save(commit=False)
        inquiry.status = CustomOrderInquiry.Status.ACCEPTED
        inquiry.save()
        form.save_reference_upload(inquiry)
        try:
            order = create_order_for_custom_inquiry(request, inquiry)
        except ValidationError as exc:
            inquiry.delete()
            form.add_error(None, "; ".join(exc.messages))
        else:
            messages.success(
                request,
                f"Custom order recorded as Oscar order {order.number}; invoice/payment is a later phase.",
            )
            return redirect("custom_order_detail", inquiry_id=inquiry.pk)
    return render(request, "home/dashboard/create_custom_order.html", {"form": form})


@staff_member_required(login_url="/dashboard/login/")
@require_http_methods(["GET", "POST"])
def custom_order_detail(request, inquiry_id: int):
    inquiry = get_object_or_404(
        CustomOrderInquiry.objects.select_related("order"),
        pk=inquiry_id,
    )
    form = CustomOrderQuoteForm(request.POST or None, instance=inquiry)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Custom-order notes and quote saved.")
        return redirect("custom_order_detail", inquiry_id=inquiry.pk)
    return render(
        request,
        "home/dashboard/custom_order_detail.html",
        {"inquiry": inquiry, "form": form},
    )


@staff_member_required(login_url="/dashboard/login/")
@require_GET
def custom_order_reference_photo(request, inquiry_id: int):
    inquiry = get_object_or_404(CustomOrderInquiry, pk=inquiry_id)
    if not inquiry.reference_photo:
        raise Http404

    try:
        image_file = inquiry.reference_photo.storage.open(
            inquiry.reference_photo.name,
            "rb",
        )
    except (FileNotFoundError, OSError):
        raise Http404 from None

    response = FileResponse(
        image_file,
        as_attachment=False,
        filename=inquiry.reference_photo_name or "reference-image",
        content_type=mimetypes.guess_type(inquiry.reference_photo_name or "")[0],
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@staff_member_required(login_url="/dashboard/login/")
@require_GET
def private_image_asset(request, asset_id: str):
    asset = get_object_or_404(
        ImageAsset,
        pk=asset_id,
        visibility=ImageAsset.Visibility.PRIVATE,
        status=ImageAsset.Status.ACTIVE,
    )
    try:
        image_file = storages["private_images"].open(asset.private_file.name, "rb")
    except (FileNotFoundError, OSError):
        raise Http404 from None

    response = FileResponse(
        image_file,
        as_attachment=False,
        filename=asset.display_name,
        content_type=asset.content_type,
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@staff_member_required(login_url="/dashboard/login/")
@require_POST
@transaction.atomic
def convert_custom_order(request, inquiry_id: int):
    inquiry = get_object_or_404(CustomOrderInquiry.objects.select_for_update(), pk=inquiry_id)
    try:
        order = create_order_for_custom_inquiry(request, inquiry)
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
        return redirect("custom_order_detail", inquiry_id=inquiry.pk)
    messages.success(
        request,
        f"Oscar order {order.number} created. It is awaiting the Stripe invoice/payment phase.",
    )
    return redirect("custom_order_detail", inquiry_id=inquiry.pk)


@staff_member_required(login_url="/dashboard/login/")
@require_http_methods(["GET", "POST"])
def record_manual_sale(request):
    form = ManualSaleForm(request.POST or None)
    line_formset = ManualSaleLineFormSet(request.POST or None, prefix="sale-lines")
    if request.method == "POST" and form.is_valid() and line_formset.is_valid():
        line_items = [
            (line_form.cleaned_data["product"], line_form.cleaned_data["quantity"])
            for line_form in line_formset
            if line_form.cleaned_data.get("product")
        ]
        if not line_items:
            form.add_error(None, "Add at least one item to the sale.")
        else:
            payment_method = form.cleaned_data["payment_method"]
            payment_label = dict(ManualSaleForm.PaymentMethod.choices)[payment_method]
            try:
                order = create_oscar_order(
                    request,
                    line_items,
                    customer_email=form.cleaned_data["customer_email"],
                    note=(
                        "In-person sale. "
                        f"Payment method: {payment_label}. "
                        f"{form.cleaned_data['notes']}"
                    ).strip(),
                    payment_method=payment_label,
                    collect_in_person=True,
                )
            except InventoryUnavailable as exc:
                form.add_error(None, str(exc))
            except ValidationError as exc:
                form.add_error(None, "; ".join(exc.messages))
            else:
                messages.success(request, f"In-person sale recorded as Oscar order {order.number}.")
                return redirect("record_manual_sale")

    return render(
        request,
        "home/dashboard/record_manual_sale.html",
        {"form": form, "line_formset": line_formset},
    )
