"""
Тесты для admin_panel: доступ, dashboard, списки.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import Profile

User = get_user_model()


class AdminAccessTestMixin:
    """Общий setup для тестов admin_panel."""

    def setUp(self):
        self.client = Client()
        # Обычный пользователь
        self.regular_user = User.objects.create_user(
            username="regular",
            password="testpass123",
            email="regular@test.com",
        )
        # Модератор
        self.moderator = User.objects.create_user(
            username="moderator",
            password="testpass123",
            email="mod@test.com",
        )
        Profile.objects.filter(user=self.moderator).update(is_moderator=True)
        # Админ
        self.admin = User.objects.create_user(
            username="admin",
            password="testpass123",
            email="admin@test.com",
            is_staff=True,
        )


class DashboardAccessTest(AdminAccessTestMixin, TestCase):
    """Тесты доступа к dashboard."""

    def test_anonymous_redirected(self):
        response = self.client.get(reverse("admin_panel:dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_regular_user_forbidden(self):
        self.client.login(username="regular", password="testpass123")
        response = self.client.get(reverse("admin_panel:dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_moderator_access(self):
        self.client.login(username="moderator", password="testpass123")
        response = self.client.get(reverse("admin_panel:dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_admin_access(self):
        self.client.login(username="admin", password="testpass123")
        response = self.client.get(reverse("admin_panel:dashboard"))
        self.assertEqual(response.status_code, 200)


class UsersListTest(AdminAccessTestMixin, TestCase):

    def test_renders_for_admin(self):
        self.client.login(username="admin", password="testpass123")
        response = self.client.get(reverse("admin_panel:users_list"))
        self.assertEqual(response.status_code, 200)

    def test_search_filter(self):
        self.client.login(username="admin", password="testpass123")
        response = self.client.get(reverse("admin_panel:users_list"), {"search": "regular"})
        self.assertEqual(response.status_code, 200)

    def test_role_filter(self):
        self.client.login(username="admin", password="testpass123")
        response = self.client.get(reverse("admin_panel:users_list"), {"role": "admin"})
        self.assertEqual(response.status_code, 200)

    def test_forbidden_for_regular_user(self):
        self.client.login(username="regular", password="testpass123")
        response = self.client.get(reverse("admin_panel:users_list"))
        self.assertEqual(response.status_code, 302)


class ListsModerationTest(AdminAccessTestMixin, TestCase):

    def test_listings_moderation_renders(self):
        self.client.login(username="admin", password="testpass123")
        response = self.client.get(reverse("admin_panel:listings_moderation"))
        self.assertEqual(response.status_code, 200)

    def test_transactions_list_renders(self):
        self.client.login(username="admin", password="testpass123")
        response = self.client.get(reverse("admin_panel:transactions_list"))
        self.assertEqual(response.status_code, 200)

    def test_disputes_list_renders(self):
        self.client.login(username="admin", password="testpass123")
        response = self.client.get(reverse("admin_panel:disputes_list"))
        self.assertEqual(response.status_code, 200)

    def test_reports_list_renders(self):
        self.client.login(username="admin", password="testpass123")
        response = self.client.get(reverse("admin_panel:reports_list"))
        self.assertEqual(response.status_code, 200)

    def test_security_logs_renders(self):
        self.client.login(username="admin", password="testpass123")
        response = self.client.get(reverse("admin_panel:security_logs"))
        self.assertEqual(response.status_code, 200)


class UserDetailTest(AdminAccessTestMixin, TestCase):

    def test_user_detail_renders(self):
        self.client.login(username="admin", password="testpass123")
        response = self.client.get(
            reverse("admin_panel:user_detail", kwargs={"user_id": self.regular_user.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_user_detail_404(self):
        self.client.login(username="admin", password="testpass123")
        response = self.client.get(reverse("admin_panel:user_detail", kwargs={"user_id": 99999}))
        self.assertEqual(response.status_code, 404)
