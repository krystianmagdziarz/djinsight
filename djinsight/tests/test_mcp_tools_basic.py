"""Tests for djinsight MCP basic tools."""

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from djinsight.mcp.tools.basic import get_page_stats, get_top_pages, list_tracked_models
from djinsight.models import ContentTypeRegistry, PageViewStatistics


class GetPageStatsTest(TestCase):
    """Tests for get_page_stats."""

    def setUp(self):
        self.ct = ContentType.objects.get_for_model(PageViewStatistics)
        self.ct_str = f"{self.ct.app_label}.{self.ct.model}"
        self.now = timezone.now()
        self.stats = PageViewStatistics.objects.create(
            content_type=self.ct,
            object_id=1,
            total_views=100,
            unique_views=50,
            first_viewed_at=self.now,
            last_viewed_at=self.now,
        )

    def test_returns_stats_for_existing_object(self):
        result = get_page_stats(self.ct_str, 1)
        self.assertEqual(result["content_type"], self.ct_str)
        self.assertEqual(result["object_id"], 1)
        self.assertEqual(result["total_views"], 100)
        self.assertEqual(result["unique_views"], 50)
        self.assertIsNotNone(result["first_viewed_at"])
        self.assertIsNotNone(result["last_viewed_at"])

    def test_returns_zeros_when_no_stats(self):
        result = get_page_stats(self.ct_str, 9999)
        self.assertEqual(result["total_views"], 0)
        self.assertEqual(result["unique_views"], 0)
        self.assertIsNone(result["first_viewed_at"])
        self.assertIsNone(result["last_viewed_at"])

    def test_returns_error_for_invalid_content_type(self):
        result = get_page_stats("invalid.model", 1)
        self.assertIn("error", result)

    def test_returns_error_for_empty_content_type(self):
        result = get_page_stats("", 1)
        self.assertIn("error", result)

    def test_object_str_representation(self):
        # The stats object itself is retrievable since we're using
        # PageViewStatistics as the content type
        result = get_page_stats(self.ct_str, self.stats.pk)
        # The object field should be present (may be str of the stats obj or None)
        self.assertIn("object", result)

    def test_dates_are_iso_format(self):
        result = get_page_stats(self.ct_str, 1)
        self.assertEqual(result["first_viewed_at"], self.now.isoformat())
        self.assertEqual(result["last_viewed_at"], self.now.isoformat())

    def test_null_dates_returned_as_none(self):
        PageViewStatistics.objects.create(
            content_type=self.ct,
            object_id=2,
            total_views=5,
            unique_views=3,
            first_viewed_at=None,
            last_viewed_at=None,
        )
        result = get_page_stats(self.ct_str, 2)
        self.assertEqual(result["total_views"], 5)
        self.assertIsNone(result["first_viewed_at"])
        self.assertIsNone(result["last_viewed_at"])


class GetTopPagesTest(TestCase):
    """Tests for get_top_pages."""

    def setUp(self):
        self.ct = ContentType.objects.get_for_model(PageViewStatistics)
        self.ct_str = f"{self.ct.app_label}.{self.ct.model}"
        self.now = timezone.now()

        # Create multiple stats entries
        for i in range(5):
            PageViewStatistics.objects.create(
                content_type=self.ct,
                object_id=i + 1,
                total_views=(i + 1) * 10,
                unique_views=(i + 1) * 5,
                last_viewed_at=self.now,
            )

    def test_returns_top_pages_by_total_views(self):
        result = get_top_pages(self.ct_str, limit=3)
        self.assertEqual(result["content_type"], self.ct_str)
        self.assertEqual(result["metric"], "total_views")
        self.assertEqual(len(result["results"]), 3)
        # Should be ordered descending by total_views
        self.assertEqual(result["results"][0]["total_views"], 50)
        self.assertEqual(result["results"][1]["total_views"], 40)
        self.assertEqual(result["results"][2]["total_views"], 30)

    def test_returns_top_pages_by_unique_views(self):
        result = get_top_pages(self.ct_str, limit=3, metric="unique_views")
        self.assertEqual(result["metric"], "unique_views")
        self.assertEqual(len(result["results"]), 3)
        self.assertEqual(result["results"][0]["unique_views"], 25)
        self.assertEqual(result["results"][1]["unique_views"], 20)
        self.assertEqual(result["results"][2]["unique_views"], 15)

    def test_default_limit_is_10(self):
        result = get_top_pages(self.ct_str)
        # We only created 5, so should return all 5
        self.assertEqual(len(result["results"]), 5)

    def test_returns_error_for_invalid_content_type(self):
        result = get_top_pages("invalid.model")
        self.assertIn("error", result)

    def test_empty_results_when_no_stats(self):
        other_ct = ContentType.objects.get_for_model(ContentTypeRegistry)
        other_ct_str = f"{other_ct.app_label}.{other_ct.model}"
        result = get_top_pages(other_ct_str)
        self.assertEqual(result["results"], [])

    def test_result_contains_expected_fields(self):
        result = get_top_pages(self.ct_str, limit=1)
        entry = result["results"][0]
        self.assertIn("object_id", entry)
        self.assertIn("object", entry)
        self.assertIn("total_views", entry)
        self.assertIn("unique_views", entry)
        self.assertIn("last_viewed_at", entry)


class ListTrackedModelsTest(TestCase):
    """Tests for list_tracked_models."""

    def setUp(self):
        self.ct = ContentType.objects.get_for_model(PageViewStatistics)
        self.registry = ContentTypeRegistry.objects.create(
            content_type=self.ct,
            enabled=True,
            track_anonymous=True,
            track_authenticated=False,
        )

    def test_returns_enabled_registries(self):
        result = list_tracked_models()
        self.assertEqual(len(result["tracked_models"]), 1)
        entry = result["tracked_models"][0]
        self.assertEqual(entry["app_label"], self.ct.app_label)
        self.assertEqual(entry["model"], self.ct.model)
        self.assertEqual(
            entry["content_type"],
            f"{self.ct.app_label}.{self.ct.model}",
        )
        self.assertTrue(entry["track_anonymous"])
        self.assertFalse(entry["track_authenticated"])

    def test_excludes_disabled_registries(self):
        other_ct = ContentType.objects.get_for_model(ContentTypeRegistry)
        ContentTypeRegistry.objects.create(
            content_type=other_ct,
            enabled=False,
        )
        result = list_tracked_models()
        self.assertEqual(len(result["tracked_models"]), 1)

    def test_returns_empty_list_when_no_registries(self):
        ContentTypeRegistry.objects.all().delete()
        result = list_tracked_models()
        self.assertEqual(result["tracked_models"], [])

    def test_multiple_enabled_registries(self):
        other_ct = ContentType.objects.get_for_model(ContentTypeRegistry)
        ContentTypeRegistry.objects.create(
            content_type=other_ct,
            enabled=True,
            track_anonymous=False,
            track_authenticated=True,
        )
        result = list_tracked_models()
        self.assertEqual(len(result["tracked_models"]), 2)
