"""Tests for the {% track %} template tag — cache safety and rendering."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.template import Context, Template
from django.test import RequestFactory, TestCase, override_settings
from django.utils.functional import SimpleLazyObject

from djinsight.models import PageViewStatistics


class TrackTagTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.factory = RequestFactory()
        ct = ContentType.objects.get_for_model(PageViewStatistics)
        self.obj = PageViewStatistics.objects.create(
            content_type=ct, object_id=1
        )
        self.users = {
            "anonymous": AnonymousUser(),
            "regular": User.objects.create_user("regular", password="x"),
            "staff": User.objects.create_user("staff", password="x", is_staff=True),
            "superuser": User.objects.create_superuser("root", "r@example.com", "x"),
        }

    def _render(self, who, flags, with_user=True):
        request = self.factory.get("/page/")
        if with_user:
            request.user = self.users[who]
        template = Template("{% load djinsight_tags %}{% track %}")
        with override_settings(
            DJINSIGHT={"USE_REDIS": False, "USE_CELERY": False, **flags}
        ):
            return template.render(Context({"request": request, "object": self.obj}))

    def test_renders_for_everyone_by_default(self):
        for who in self.users:
            with self.subTest(who=who):
                self.assertIn("<script>", self._render(who, {}))

    def test_renders_for_staff_even_when_track_staff_false(self):
        """Tag must always render the script — exclusion is in the view."""
        self.assertIn("<script>", self._render("staff", {"TRACK_STAFF": False}))

    def test_renders_for_superuser_even_when_track_superuser_false(self):
        self.assertIn("<script>", self._render("superuser", {"TRACK_SUPERUSER": False}))

    def test_renders_for_authenticated_even_when_track_authenticated_false(self):
        self.assertIn("<script>", self._render("regular", {"TRACK_AUTHENTICATED": False}))

    def test_does_not_access_request_user(self):
        """Tag must not resolve request.user so it doesn't add Vary: Cookie."""
        request = self.factory.get("/page/")

        def explode():
            raise AssertionError("request.user was accessed")

        request.user = SimpleLazyObject(explode)
        template = Template("{% load djinsight_tags %}{% track %}")
        with override_settings(DJINSIGHT={"USE_REDIS": False, "USE_CELERY": False}):
            html = template.render(Context({"request": request, "object": self.obj}))
        self.assertIn("<script>", html)

    def test_no_request_returns_empty(self):
        template = Template("{% load djinsight_tags %}{% track %}")
        with override_settings(DJINSIGHT={"USE_REDIS": False, "USE_CELERY": False}):
            html = template.render(Context({"object": self.obj}))
        self.assertEqual(html.strip(), "")

    def test_tracking_disabled_returns_empty(self):
        html = self._render("anonymous", {"ENABLE_TRACKING": False})
        self.assertEqual(html.strip(), "")
