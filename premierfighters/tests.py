from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AdminDocsRouteTests(TestCase):
    def test_docs_page_is_available_for_staff_user(self):
        user = get_user_model().objects.create(
            username="docs_admin", is_staff=True, is_superuser=True
        )
        self.client.force_login(user)

        response = self.client.get(reverse("django-admindocs-docroot"))

        self.assertEqual(response.status_code, 200)
