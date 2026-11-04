from home.models import BlogIndexPage, BlogPostPage, PolicyPage


def editorial_navigation(request):
    """Expose published editorial and policy pages to shared templates."""
    blog_index = BlogIndexPage.objects.live().first()
    if blog_index and not BlogPostPage.objects.child_of(blog_index).live().exists():
        blog_index = None
    policy_page = PolicyPage.objects.live().filter(slug="shipping-returns").first()
    privacy_page = PolicyPage.objects.live().filter(slug="privacy").first()
    return {
        "blog_index": blog_index,
        "policy_page": policy_page,
        "privacy_page": privacy_page,
    }
