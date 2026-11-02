from home.models import BlogIndexPage, BlogPostPage


def editorial_navigation(request):
    """Expose the blog link only when the maker has published a real post."""
    blog_index = BlogIndexPage.objects.live().first()
    if blog_index and not BlogPostPage.objects.child_of(blog_index).live().exists():
        blog_index = None
    return {"blog_index": blog_index}
