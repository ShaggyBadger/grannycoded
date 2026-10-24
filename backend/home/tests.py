from django.test import TestCase
from wagtail.models import Site

from .models import HomePage


class StarterHomePageTests(TestCase):
    def test_default_site_root_is_the_editable_home_page(self):
        root_page = Site.objects.get(is_default_site=True).root_page.specific

        self.assertIsInstance(root_page, HomePage)

    def test_home_page_renders_at_the_site_root(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your new website starts here.")
