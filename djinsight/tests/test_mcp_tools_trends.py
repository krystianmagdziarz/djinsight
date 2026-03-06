"""Tests for djinsight MCP tools trends module."""

from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from djinsight.mcp.tools.trends import get_trending_pages
from djinsight.models import PageViewEvent


class GetTrendingPagesTest(TestCase):
    """Tests for get_trending_pages."""

    def setUp(self):
        self.ct = ContentType.objects.get(app_label="contenttypes", model="contenttype")
        self.content_type_str = "contenttypes.contenttype"
        self.now = timezone.now()

    def _create_events(self, object_id, count, timestamp):
        """Helper to create multiple PageViewEvent records."""
        events = []
        for i in range(count):
            events.append(
                PageViewEvent(
                    content_type=self.ct,
                    object_id=object_id,
                    url=f"/page/{object_id}/",
                    session_key=f"session-{object_id}-{timestamp.isoformat()}-{i}",
                    timestamp=timestamp,
                )
            )
        PageViewEvent.objects.bulk_create(events)

    def test_direction_up_returns_growing_first(self):
        """Objects with highest growth should appear first when direction='up'."""
        # Current period: last 7 days (week)
        current_time = self.now - timedelta(days=2)
        # Previous period: 7 days before that
        previous_time = self.now - timedelta(days=10)

        # Object 1: grew from 2 to 10 (growth = 400%)
        self._create_events(1, 2, previous_time)
        self._create_events(1, 10, current_time)

        # Object 2: grew from 5 to 6 (growth = 20%)
        self._create_events(2, 5, previous_time)
        self._create_events(2, 6, current_time)

        # Object 3: grew from 0 to 5 (growth = 100%, new page)
        self._create_events(3, 5, current_time)

        result = get_trending_pages(
            self.content_type_str, period="week", direction="up"
        )

        self.assertEqual(result["content_type"], self.content_type_str)
        self.assertEqual(result["period"], "week")
        self.assertEqual(result["direction"], "up")
        self.assertNotIn("error", result)

        results = result["results"]
        self.assertGreaterEqual(len(results), 2)

        # Object 1 (400%) should be before Object 3 (100%) and Object 2 (20%)
        growth_rates = [r["growth_rate"] for r in results]
        self.assertEqual(growth_rates, sorted(growth_rates, reverse=True))

        # Verify Object 1 is first
        self.assertEqual(results[0]["object_id"], 1)
        self.assertEqual(results[0]["current_views"], 10)
        self.assertEqual(results[0]["previous_views"], 2)
        self.assertEqual(results[0]["growth_rate"], 400.0)
        self.assertEqual(results[0]["delta"], 8)

    def test_direction_down_returns_declining_first(self):
        """Objects with biggest decline should appear first when direction='down'."""
        current_time = self.now - timedelta(days=2)
        previous_time = self.now - timedelta(days=10)

        # Object 1: declined from 10 to 2 (growth = -80%)
        self._create_events(1, 10, previous_time)
        self._create_events(1, 2, current_time)

        # Object 2: declined from 5 to 4 (growth = -20%)
        self._create_events(2, 5, previous_time)
        self._create_events(2, 4, current_time)

        # Object 3: grew from 1 to 5 (growth = 400%)
        self._create_events(3, 1, previous_time)
        self._create_events(3, 5, current_time)

        result = get_trending_pages(
            self.content_type_str, period="week", direction="down"
        )

        results = result["results"]
        self.assertGreaterEqual(len(results), 2)

        # Growth rates should be ascending (most negative first)
        growth_rates = [r["growth_rate"] for r in results]
        self.assertEqual(growth_rates, sorted(growth_rates))

        # Object 1 (-80%) should be first
        self.assertEqual(results[0]["object_id"], 1)
        self.assertEqual(results[0]["growth_rate"], -80.0)
        self.assertEqual(results[0]["delta"], -8)

    def test_invalid_content_type(self):
        """Invalid content type should return error with empty results."""
        result = get_trending_pages("nonexistent.model", period="week")

        self.assertEqual(result["content_type"], "nonexistent.model")
        self.assertIn("error", result)
        self.assertEqual(result["results"], [])

    def test_new_page_growth_rate_is_100(self):
        """A page with views only in current period should have growth_rate=100."""
        current_time = self.now - timedelta(days=2)
        self._create_events(1, 5, current_time)

        result = get_trending_pages(
            self.content_type_str, period="week", direction="up"
        )

        results = result["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["growth_rate"], 100.0)
        self.assertEqual(results[0]["previous_views"], 0)
        self.assertEqual(results[0]["current_views"], 5)

    def test_disappeared_page_has_negative_growth(self):
        """A page with views only in previous period should have -100% growth."""
        previous_time = self.now - timedelta(days=10)
        self._create_events(1, 5, previous_time)

        result = get_trending_pages(
            self.content_type_str, period="week", direction="down"
        )

        results = result["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["growth_rate"], -100.0)
        self.assertEqual(results[0]["current_views"], 0)
        self.assertEqual(results[0]["previous_views"], 5)

    def test_limit_parameter(self):
        """Results should be limited to the specified number."""
        current_time = self.now - timedelta(days=2)

        for obj_id in range(1, 6):
            self._create_events(obj_id, obj_id, current_time)

        result = get_trending_pages(
            self.content_type_str, period="week", direction="up", limit=3
        )

        self.assertEqual(len(result["results"]), 3)

    def test_no_events_returns_empty(self):
        """No events should return empty results list."""
        result = get_trending_pages(self.content_type_str, period="week")

        self.assertEqual(result["results"], [])
        self.assertNotIn("error", result)

    def test_result_contains_object_name(self):
        """Each result should contain an 'object' field with the object name."""
        current_time = self.now - timedelta(days=2)
        self._create_events(self.ct.pk, 3, current_time)

        result = get_trending_pages(self.content_type_str, period="week")

        results = result["results"]
        self.assertEqual(len(results), 1)
        self.assertIn("object", results[0])
        # The object name should be the str() of the ContentType instance
        self.assertIsInstance(results[0]["object"], str)
        self.assertNotEqual(results[0]["object"], "")

    def test_result_contains_delta(self):
        """Each result should include a delta field (current - previous)."""
        current_time = self.now - timedelta(days=2)
        previous_time = self.now - timedelta(days=10)

        self._create_events(1, 3, previous_time)
        self._create_events(1, 8, current_time)

        result = get_trending_pages(self.content_type_str, period="week")

        results = result["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["delta"], 5)
