"""Tests for djinsight MCP search tools."""

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from djinsight.mcp.tools.search import search_pages
from djinsight.models import ContentTypeRegistry, PageViewStatistics


class SearchPagesTest(TestCase):
    """Tests for search_pages."""

    def setUp(self):
        self.ct = ContentType.objects.get_for_model(PageViewStatistics)
        self.ct_str = f"{self.ct.app_label}.{self.ct.model}"
        self.now = timezone.now()

        # Register PageViewStatistics as a tracked model
        self.registry = ContentTypeRegistry.objects.create(
            content_type=self.ct,
            enabled=True,
        )

        # Create some stats entries (they are also the objects we search)
        self.stats1 = PageViewStatistics.objects.create(
            content_type=self.ct,
            object_id=1,
            total_views=100,
            unique_views=50,
            first_viewed_at=self.now,
            last_viewed_at=self.now,
        )
        self.stats2 = PageViewStatistics.objects.create(
            content_type=self.ct,
            object_id=2,
            total_views=200,
            unique_views=80,
            first_viewed_at=self.now,
            last_viewed_at=self.now,
        )
        self.stats3 = PageViewStatistics.objects.create(
            content_type=self.ct,
            object_id=3,
            total_views=50,
            unique_views=20,
            first_viewed_at=self.now,
            last_viewed_at=self.now,
        )

    def test_empty_query_returns_error(self):
        result = search_pages("")
        self.assertIn("error", result)

    def test_none_query_returns_error(self):
        result = search_pages(None)
        self.assertIn("error", result)

    def test_whitespace_query_returns_error(self):
        result = search_pages("   ")
        self.assertIn("error", result)

    def test_search_returns_results(self):
        # PageViewStatistics.__str__ returns e.g. "djinsight | page view statistics #1: 100 views"
        # Search for "views" which should appear in str() of all stats objects
        result = search_pages("views")
        self.assertNotIn("error", result)
        self.assertEqual(result["query"], "views")
        self.assertGreater(result["total_results"], 0)
        self.assertGreater(len(result["results"]), 0)

    def test_search_results_sorted_by_total_views_desc(self):
        result = search_pages("views")
        views = [r["total_views"] for r in result["results"]]
        self.assertEqual(views, sorted(views, reverse=True))

    def test_search_result_contains_expected_fields(self):
        result = search_pages("views")
        self.assertGreater(len(result["results"]), 0)
        entry = result["results"][0]
        self.assertIn("content_type", entry)
        self.assertIn("object_id", entry)
        self.assertIn("object", entry)
        self.assertIn("total_views", entry)
        self.assertIn("unique_views", entry)

    def test_search_with_content_type_filter(self):
        result = search_pages("views", content_type=self.ct_str)
        self.assertNotIn("error", result)
        self.assertGreater(result["total_results"], 0)
        # All results should have the specified content type
        for entry in result["results"]:
            self.assertEqual(entry["content_type"], self.ct_str)

    def test_search_with_invalid_content_type(self):
        result = search_pages("views", content_type="invalid.model")
        self.assertIn("error", result)

    def test_search_respects_limit(self):
        result = search_pages("views", limit=1)
        self.assertLessEqual(len(result["results"]), 1)

    def test_search_no_matches(self):
        result = search_pages("xyznonexistentquery123")
        self.assertNotIn("error", result)
        self.assertEqual(result["total_results"], 0)
        self.assertEqual(result["results"], [])

    def test_search_only_enabled_registries(self):
        # Disable the registry
        self.registry.enabled = False
        self.registry.save()

        # Without content_type filter, should find nothing (no enabled registries)
        result = search_pages("views")
        self.assertEqual(result["total_results"], 0)

    def test_search_with_content_type_bypasses_registry(self):
        # Even with registry disabled, explicit content_type should work
        self.registry.enabled = False
        self.registry.save()

        result = search_pages("views", content_type=self.ct_str)
        self.assertNotIn("error", result)
        self.assertGreater(result["total_results"], 0)

    def test_search_stats_values(self):
        # Search and verify stats are correctly attached
        result = search_pages("views", content_type=self.ct_str)
        # The top result (by total_views) should be stats2 with 200 views
        top = result["results"][0]
        self.assertEqual(top["total_views"], 200)
        self.assertEqual(top["unique_views"], 80)
