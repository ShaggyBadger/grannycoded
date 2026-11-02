from django import forms
from django.db import models
from django.db.models import F, Value
from django.db.models.functions import Coalesce
from django.forms import formset_factory
from oscar.core.loading import get_model

from home.models import CustomOrderInquiry, ImageAsset
from home.services.image_assets import save_uploaded_image


class ReferencePhotoUploadMixin:
    """Store customer reference photos as private ULID-backed image assets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reference_upload"] = forms.ImageField(
            label="Reference photo",
            required=False,
        )

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            self.save_m2m()
            self.save_reference_upload(instance)
        else:
            self.save_m2m = self._save_m2m
        return instance

    def clean_reference_upload(self):
        image = self.cleaned_data.get("reference_upload")
        if image and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Reference photos must be 5 MB or smaller.")
        return image

    def save_reference_upload(self, instance):
        image = self.cleaned_data.get("reference_upload")
        if not image:
            return None
        asset = save_uploaded_image(
            image,
            visibility=ImageAsset.Visibility.PRIVATE,
            category=ImageAsset.Category.CUSTOM_REFERENCE,
            display_name=image.name,
        )
        instance.reference_asset = asset
        instance.reference_photo_name = asset.display_name
        instance.save(update_fields=["reference_asset", "reference_photo_name", "updated_at"])
        return asset


class CustomOrderInquiryForm(ReferencePhotoUploadMixin, forms.ModelForm):
    class Meta:
        model = CustomOrderInquiry
        fields = ["name", "email", "request_details"]
        widgets = {
            "request_details": forms.Textarea(
                attrs={"rows": 6, "maxlength": 5000}
            )
        }

class CustomOrderQuoteForm(forms.ModelForm):
    class Meta:
        model = CustomOrderInquiry
        fields = ["status", "quoted_total", "quoted_shipping", "shipping_note", "maker_notes"]
        widgets = {"maker_notes": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["quoted_total"].help_text = (
            "Final amount agreed with the customer, including any shipping."
        )
        self.fields["quoted_shipping"].help_text = "Shipping portion included in the quoted total."
        if self.instance.order_id:
            locked_fields = ("status", "quoted_total", "quoted_shipping", "shipping_note")
            for field_name in locked_fields:
                self.fields[field_name].disabled = True
        else:
            self.fields["status"].choices = [
                choice
                for choice in self.fields["status"].choices
                if choice[0] != CustomOrderInquiry.Status.CONVERTED
            ]

    def clean(self):
        cleaned_data = super().clean()
        total = cleaned_data.get("quoted_total")
        shipping = cleaned_data.get("quoted_shipping") or 0
        status = cleaned_data.get("status")
        if status in {
            CustomOrderInquiry.Status.QUOTED,
            CustomOrderInquiry.Status.ACCEPTED,
        } and total is None:
            self.add_error("quoted_total", "Enter the agreed quote before marking it quoted or accepted.")
        if total is not None and total <= 0:
            self.add_error("quoted_total", "The quoted total must be greater than zero.")
        if total is not None and shipping >= total:
            self.add_error(
                "quoted_shipping",
                "Shipping must be less than the total so the custom item has a positive price.",
            )
        return cleaned_data


class CustomOrderCreateForm(ReferencePhotoUploadMixin, forms.ModelForm):
    class Meta:
        model = CustomOrderInquiry
        fields = [
            "name",
            "email",
            "request_details",
            "quoted_total",
            "quoted_shipping",
            "shipping_note",
            "maker_notes",
        ]
        widgets = {
            "request_details": forms.Textarea(attrs={"rows": 5}),
            "maker_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        total = cleaned_data.get("quoted_total")
        shipping = cleaned_data.get("quoted_shipping") or 0
        if total is not None and total <= 0:
            self.add_error("quoted_total", "The agreed total must be greater than zero.")
        if total is not None and shipping >= total:
            self.add_error(
                "quoted_shipping",
                "Shipping must be less than the total so the custom item has a positive price.",
            )
        return cleaned_data


class ManualSaleForm(forms.Form):
    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Cash"
        CARD = "card", "Card reader"
        OTHER = "other", "Other"

    payment_method = forms.ChoiceField(choices=PaymentMethod.choices)
    customer_email = forms.EmailField(required=False)
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))


class ManualSaleLineForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=get_model("catalogue", "Product").objects.none(),
        empty_label="Choose a product",
    )
    quantity = forms.IntegerField(min_value=1, max_value=99, initial=1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        Product = get_model("catalogue", "Product")
        self.fields["product"].queryset = (
            Product.objects.filter(
                structure__in=(Product.STANDALONE, Product.CHILD),
                stockrecords__partner__code="grannycoded",
                stockrecords__num_in_stock__gt=Coalesce(
                    F("stockrecords__num_allocated"), Value(0)
                ),
            )
            .select_related("product_class")
            .distinct()
            .order_by("title")
        )


ManualSaleLineFormSet = formset_factory(
    ManualSaleLineForm,
    extra=2,
    min_num=1,
    max_num=10,
    validate_min=True,
    validate_max=True,
)
