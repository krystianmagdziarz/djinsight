"""Tests for djinsight views."""

import json
from types import SimpleNamespace

from django.contrib.contenttypes.models import ContentType
from django.test import Client, TestCase
from django.urls import reverse

from djinsight.conf import djinsight_settings
from djinsight.models import PageViewStatistics


class RecordPageViewTest(TestCase):
    """Test record_page_view endpoint."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.content_type = ContentType.objects.get_for_model(PageViewStatistics)

    def test_record_view_creates_event(self):
        """Test that posting to record_page_view creates an event."""
        data = {
            "content_type": f"{self.content_type.app_label}.{self.content_type.model}",
            "object_id": 1,
            "url": "/test/",
            "referrer": "https://example.com",
            "user_agent": "Test Agent",
        }

        response = self.client.post(
            reverse("djinsight:record_page_view"),
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result.get("success"))

    def test_record_view_requires_object_id(self):
        """Test that object_id is required."""
        data = {
            "content_type": f"{self.content_type.app_label}.{self.content_type.model}",
            "url": "/test/",
        }

        response = self.client.post(
            reverse("djinsight:record_page_view"),
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_record_view_requires_content_type(self):
        """Test that content_type is required."""
        data = {
            "object_id": 1,
            "url": "/test/",
        }

        response = self.client.post(
            reverse("djinsight:record_page_view"),
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)


AUTH_MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]


class UserExclusionViewTest(TestCase):
    """Test that record_page_view honours TRACK_* settings."""

    def setUp(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        self.client = Client()
        ct = ContentType.objects.get_for_model(PageViewStatistics)
        self.payload = json.dumps(
            {"content_type": f"{ct.app_label}.{ct.model}", "object_id": 1, "url": "/t/"}
        )
        self.users = {
            "regular": User.objects.create_user("regular", password="x"),
            "staff": User.objects.create_user("staff", password="x", is_staff=True),
            "superuser": User.objects.create_superuser("root", "r@example.com", "x"),
            "super_nonstaff": User.objects.create_user(
                "sn", password="x", is_superuser=True
            ),
        }

    def _post(self, who, flags):
        from unittest import mock

        from django.test import override_settings

        if who != "anonymous":
            self.client.force_login(self.users[who])
        with override_settings(
            MIDDLEWARE=AUTH_MIDDLEWARE,
            DJINSIGHT={"USE_REDIS": False, "USE_CELERY": False, **flags},
        ):
            with mock.patch(
                "djinsight.providers.database.DatabaseProvider.record_view",
                return_value={"success": True},
            ) as record:
                response = self.client.post(
                    reverse("djinsight:record_page_view"),
                    data=self.payload,
                    content_type="application/json",
                )
        return response, record

    def assertExcluded(self, who, flags):
        response, record = self._post(who, flags)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "excluded"})
        record.assert_not_called()

    def assertTracked(self, who, flags):
        response, record = self._post(who, flags)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("success"))
        record.assert_called_once()

    def test_defaults_track_everyone(self):
        for who in ["anonymous", "regular", "staff", "superuser"]:
            with self.subTest(who=who):
                self.client = Client()
                self.assertTracked(who, {})

    def test_track_anonymous_false(self):
        self.assertExcluded("anonymous", {"TRACK_ANONYMOUS": False})

    def test_track_anonymous_false_keeps_authenticated(self):
        self.assertTracked("regular", {"TRACK_ANONYMOUS": False})

    def test_track_authenticated_false_excludes_all_logged_in(self):
        for who in ["regular", "staff", "superuser"]:
            with self.subTest(who=who):
                self.client = Client()
                self.assertExcluded(who, {"TRACK_AUTHENTICATED": False})

    def test_track_authenticated_false_keeps_anonymous(self):
        self.assertTracked("anonymous", {"TRACK_AUTHENTICATED": False})

    def test_track_staff_false(self):
        self.assertExcluded("staff", {"TRACK_STAFF": False})

    def test_track_staff_false_keeps_regular(self):
        self.assertTracked("regular", {"TRACK_STAFF": False})

    def test_track_superuser_false(self):
        self.assertExcluded("superuser", {"TRACK_SUPERUSER": False})

    def test_track_superuser_false_keeps_staff(self):
        self.assertTracked("staff", {"TRACK_SUPERUSER": False})

    def test_superuser_staff_excluded_by_track_staff_false_alone(self):
        self.assertExcluded(
            "superuser", {"TRACK_SUPERUSER": True, "TRACK_STAFF": False}
        )

    def test_superuser_without_staff_not_excluded_by_track_staff_false(self):
        self.assertTracked("super_nonstaff", {"TRACK_STAFF": False})

    def test_custom_user_model_without_is_staff(self):
        """User model without is_staff/is_superuser must not cause 500."""
        user = SimpleNamespace(is_authenticated=True)
        self.assertTrue(djinsight_settings.should_track_user(user))

        from unittest import mock

        from django.test import override_settings

        with override_settings(
            MIDDLEWARE=AUTH_MIDDLEWARE,
            DJINSIGHT={"USE_REDIS": False, "USE_CELERY": False, "TRACK_STAFF": False},
        ):
            with mock.patch(
                "djinsight.providers.database.DatabaseProvider.record_view",
                return_value={"success": True},
            ) as record:
                with mock.patch(
                    "djinsight.views.djinsight_settings.should_track_user",
                    wraps=djinsight_settings.should_track_user,
                ):
                    # Simulate request.user = object without is_staff
                    with mock.patch(
                        "django.contrib.auth.middleware.AuthenticationMiddleware.process_request",
                        side_effect=lambda req: setattr(req, "user", user),
                    ):
                        response = self.client.post(
                            reverse("djinsight:record_page_view"),
                            data=self.payload,
                            content_type="application/json",
                        )
        self.assertEqual(response.status_code, 200)
        # User has no is_staff so TRACK_STAFF=False does not exclude them
        record.assert_called_once()

    def test_excluded_does_not_create_session(self):
        from django.test import override_settings

        with override_settings(
            MIDDLEWARE=AUTH_MIDDLEWARE,
            DJINSIGHT={
                "USE_REDIS": False,
                "USE_CELERY": False,
                "TRACK_ANONYMOUS": False,
            },
        ):
            response = self.client.post(
                reverse("djinsight:record_page_view"),
                data=self.payload,
                content_type="application/json",
            )
        self.assertEqual(response.json(), {"status": "excluded"})
        self.assertNotIn("sessionid", response.cookies)
