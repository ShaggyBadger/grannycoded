from django.urls import reverse
from wagtail import hooks
from wagtail.admin.menu import MenuItem

from home.models import BlogIndexPage


class BlogPostsMenuItem(MenuItem):
    """Link staff directly to the Blog page's list of posts."""

    def __init__(self):
        super().__init__(
            "Blog posts",
            url="",
            name="blog_posts",
            icon_name="doc-full-inverse",
            order=110,
        )

    def is_shown(self, request):
        if not request.user.is_staff:
            return False

        blog = BlogIndexPage.objects.order_by("path").first()
        if blog is None:
            return False

        self.url = reverse("wagtailadmin_explore", args=[blog.pk])
        return True


@hooks.register("register_admin_menu_item")
def register_blog_posts_menu_item():
    return BlogPostsMenuItem()
