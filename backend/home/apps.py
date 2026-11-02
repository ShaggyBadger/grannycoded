from django.apps import AppConfig


class HomeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "home"

    def ready(self):
        from home import signals  # noqa: F401
        from home.models import BlogPostPage
        from home.wagtail_forms import BlogPostPageForm

        BlogPostPage.base_form_class = BlogPostPageForm
