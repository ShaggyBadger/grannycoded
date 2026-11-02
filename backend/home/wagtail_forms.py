from pathlib import PurePosixPath

from django import forms
from django.core.exceptions import ValidationError
from wagtail.admin.forms.pages import WagtailAdminPageForm

from home.models import BlogPostPage, ImageAsset
from home.services.image_assets import (
    ALLOWED_IMAGE_SUFFIXES,
    save_uploaded_image,
)


MAX_COVER_UPLOAD_BYTES = 20 * 1024 * 1024


class BlogPostPageForm(WagtailAdminPageForm):
    cover_upload = forms.ImageField(
        label="Choose an image",
        required=False,
        widget=forms.ClearableFileInput(
            attrs={
                "accept": ".jpg,.jpeg,.png,.webp,.avif",
                "class": "grannycoded-cover-upload",
            }
        ),
    )

    class Meta:
        model = BlogPostPage
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields["cover_upload"]
        field.help_text = (
            "Choose a JPG, PNG, WebP, or AVIF image up to 20 MB. "
            "Leave this empty to keep the current cover."
        )
        if self.instance.cover_asset_id:
            field.help_text += (
                f" Current cover: {self.instance.cover_asset.display_name}."
            )
        else:
            field.help_text += " No cover image is set yet."

    def clean_cover_upload(self):
        upload = self.cleaned_data.get("cover_upload")
        if upload is None:
            return None

        suffix = PurePosixPath(upload.name).suffix.lower()
        if suffix not in ALLOWED_IMAGE_SUFFIXES:
            raise ValidationError("Upload a JPG, PNG, WebP, or AVIF image.")
        if upload.size > MAX_COVER_UPLOAD_BYTES:
            raise ValidationError("Cover images must be 20 MB or smaller.")
        return upload

    def save(self, commit=True):
        upload = self.cleaned_data.get("cover_upload")
        if upload:
            asset = getattr(self, "_uploaded_cover_asset", None)
            if asset is None:
                asset = save_uploaded_image(
                    upload,
                    visibility=ImageAsset.Visibility.PUBLIC,
                    category=ImageAsset.Category.EDITORIAL,
                )
                self._uploaded_cover_asset = asset
            self.instance.cover_asset = asset

        return super().save(commit=commit)
