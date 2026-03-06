"""Tests for djinsight cross-model MCP tools."""

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from djinsight.mcp.tools.cross_model import compare_content_types, get_site_overview
from djinsight.models import PageViewEvent, PageViewStatistics, PageViewSummary


class GetSiteOverviewTest(TestCase):
    """Tests for get_site_overview."""

    def setUp(self):
        self.ct_stats = ContentType.objects.get_for_model(PageViewStatistics)
        self.ct_summary = ContentType.objects.get_for_model(PageViewSummary)

    def test_empty_site(self):
        result = get_site_overview()
        self.assertEqual(result["total_views"], 0)
        self.assertEqual(result["total_unique_views"], 0)
        self.assertEqual(result["tracked_objects"], 0)
        self.assertEqual(result["by_content_type"], [])

    def test_single_content_type(self):
        PageViewStatistics.objects.create(
            content_type=self.ct_stats, object_id=1, total_views=100, unique_views=50
        )
        PageViewStatistics.objects.create(
            content_type=self.ct_stats, object_id=2, total_views=200, unique_views=80
        )

        result = get_site_overview()
        self.assertEqual(result["total_views"], 300)
        self.assertEqual(result["total_unique_views"], 130)
        self.assertEqual(result["tracked_objects"], 2)
        self.assertEqual(len(result["by_content_type"]), 1)

        ct_entry = result["by_content_type"][0]
        self.assertEqual(
            ct_entry["content_type"],
            f"{self.ct_stats.app_label}.{self.ct_stats.model}",
        )
        self.assertEqual(ct_entry["total_views"], 300)
        self.assertEqual(ct_entry["unique_views"], 130)
        self.assertEqual(ct_entry["object_count"], 2)

    def test_multiple_content_types(self):
        PageViewStatistics.objects.create(
            content_type=self.ct_stats, object_id=1, total_views=100, unique_views=50
        )
        PageViewStatistics.objects.create(
            content_type=self.ct_summary, object_id=1, total_views=300, unique_views=150
        )

        result = get_site_overview()
        self.assertEqual(result["total_views"], 400)
        self.assertEqual(result["total_unique_views"], 200)
        self.assertEqual(result["tracked_objects"], 2)
        self.assertEqual(len(result["by_content_type"]), 2)

        # Should be sorted by total_views desc
        self.assertEqual(result["by_content_type"][0]["total_views"], 300)
        self.assertEqual(result["by_content_type"][1]["total_views"], 100)


class CompareContentTypesTest(TestCase):
    """Tests for compare_content_types."""

    def setUp(self):
        self.ct_stats = ContentType.objects.get_for_model(PageViewStatistics)
        self.ct_summary = ContentType.objects.get_for_model(PageViewSummary)
        self.now = timezone.now()

        # Create events for ct_stats
        for i in range(5):
            PageViewEvent.objects.create(
                content_type=self.ct_stats,
                object_id=1,
                url="/stats/1",
                session_key=f"session-stats-{i}",
                timestamp=self.now,
            )

        # Create events for ct_summary (more events, some sharing session keys)
        for i in range(8):
            PageViewEvent.objects.create(
                content_type=self.ct_summary,
                object_id=1,
                url="/summary/1",
                session_key=f"session-summary-{i % 4}",
                timestamp=self.now,
            )

    def test_compare_both_types(self):
        ct_stats_str = f"{self.ct_stats.app_label}.{self.ct_stats.model}"
        ct_summary_str = f"{self.ct_summary.app_label}.{self.ct_summary.model}"

        result = compare_content_types([ct_stats_str, ct_summary_str], period="month")

        self.assertEqual(result["period"], "month")
        self.assertEqual(len(result["content_types"]), 2)

        # Summary has 8 events, should be first (sorted desc)
        self.assertEqual(result["content_types"][0]["content_type"], ct_summary_str)
        self.assertEqual(result["content_types"][0]["total_views"], 8)
        self.assertEqual(result["content_types"][0]["unique_views"], 4)

        # Stats has 5 events
        self.assertEqual(result["content_types"][1]["content_type"], ct_stats_str)
        self.assertEqual(result["content_types"][1]["total_views"], 5)
        self.assertEqual(result["content_types"][1]["unique_views"], 5)

    def test_skips_invalid_content_type(self):
        ct_stats_str = f"{self.ct_stats.app_label}.{self.ct_stats.model}"

        result = compare_content_types(
            [ct_stats_str, "nonexistent.model"], period="month"
        )

        self.assertEqual(len(result["content_types"]), 1)
        self.assertEqual(result["content_types"][0]["content_type"], ct_stats_str)

    def test_all_invalid_content_types(self):
        result = compare_content_types(["bad.type", "also.bad"], period="month")
        self.assertEqual(result["content_types"], [])

    def test_empty_content_types_list(self):
        result = compare_content_types([], period="month")
        self.assertEqual(result["content_types"], [])
        self.assertEqual(result["period"], "month")
