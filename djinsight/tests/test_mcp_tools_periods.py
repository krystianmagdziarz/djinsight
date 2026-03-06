"""Tests for djinsight MCP period tools."""

from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from djinsight.mcp.tools.periods import compare_periods, get_period_stats
from djinsight.models import PageViewEvent


class PeriodToolsTestBase(TestCase):
    """Base class with helper methods for period tool tests."""

    def setUp(self):
        self.ct = ContentType.objects.get(app_label="contenttypes", model="contenttype")
        self.ct_str = "contenttypes.contenttype"
        self.object_id = 1
        self.now = timezone.now()

    def _create_event(self, days_ago=0, hours_ago=0, session_key="session1"):
        """Create a PageViewEvent at a given time offset."""
        ts = self.now - timedelta(days=days_ago, hours=hours_ago)
        return PageViewEvent.objects.create(
            content_type=self.ct,
            object_id=self.object_id,
            url="/test/",
            session_key=session_key,
            timestamp=ts,
        )


class GetPeriodStatsTest(PeriodToolsTestBase):
    """Tests for get_period_stats."""

    def test_invalid_content_type(self):
        result = get_period_stats("invalid.model", 1)
        self.assertIn("error", result)

    def test_no_events_returns_zero(self):
        result = get_period_stats(self.ct_str, self.object_id, period="week")
        self.assertEqual(result["total_views"], 0)
        self.assertEqual(result["unique_views"], 0)
        self.assertEqual(result["daily_breakdown"], [])

    def test_total_views_count(self):
        self._create_event(days_ago=0, session_key="s1")
        self._create_event(days_ago=0, session_key="s2")
        self._create_event(days_ago=1, session_key="s1")

        result = get_period_stats(self.ct_str, self.object_id, period="week")
        self.assertEqual(result["total_views"], 3)

    def test_unique_views_count(self):
        self._create_event(days_ago=0, session_key="s1")
        self._create_event(days_ago=0, session_key="s1")
        self._create_event(days_ago=0, session_key="s2")

        result = get_period_stats(self.ct_str, self.object_id, period="week")
        self.assertEqual(result["unique_views"], 2)

    def test_daily_breakdown_groups_by_date(self):
        self._create_event(days_ago=0, session_key="s1")
        self._create_event(days_ago=0, session_key="s2")
        self._create_event(days_ago=1, session_key="s1")

        result = get_period_stats(self.ct_str, self.object_id, period="week")
        breakdown = result["daily_breakdown"]

        self.assertGreaterEqual(len(breakdown), 1)
        total_from_breakdown = sum(d["views"] for d in breakdown)
        self.assertEqual(total_from_breakdown, 3)

    def test_events_outside_period_excluded(self):
        # Event 10 days ago is outside the default "week" (last 7 days)
        self._create_event(days_ago=10, session_key="s1")
        self._create_event(days_ago=0, session_key="s2")

        result = get_period_stats(self.ct_str, self.object_id, period="week")
        self.assertEqual(result["total_views"], 1)

    def test_today_period(self):
        self._create_event(days_ago=0, session_key="s1")
        self._create_event(days_ago=1, session_key="s2")

        result = get_period_stats(self.ct_str, self.object_id, period="today")
        self.assertEqual(result["total_views"], 1)
        self.assertEqual(result["period"], "today")

    def test_month_period(self):
        self._create_event(days_ago=0, session_key="s1")
        self._create_event(days_ago=15, session_key="s2")
        self._create_event(days_ago=40, session_key="s3")

        result = get_period_stats(self.ct_str, self.object_id, period="month")
        self.assertEqual(result["total_views"], 2)

    def test_custom_period(self):
        target_date = self.now - timedelta(days=5)
        start_str = (self.now - timedelta(days=7)).strftime("%Y-%m-%d")
        end_str = (self.now - timedelta(days=3)).strftime("%Y-%m-%d")

        PageViewEvent.objects.create(
            content_type=self.ct,
            object_id=self.object_id,
            url="/test/",
            session_key="s1",
            timestamp=target_date,
        )

        result = get_period_stats(
            self.ct_str,
            self.object_id,
            period="custom",
            start_date=start_str,
            end_date=end_str,
        )
        self.assertEqual(result["total_views"], 1)
        self.assertEqual(result["period"], "custom")

    def test_result_contains_expected_keys(self):
        result = get_period_stats(self.ct_str, self.object_id, period="week")
        expected_keys = {
            "content_type",
            "object_id",
            "period",
            "start_date",
            "end_date",
            "total_views",
            "unique_views",
            "daily_breakdown",
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_different_object_ids_isolated(self):
        self._create_event(days_ago=0, session_key="s1")
        PageViewEvent.objects.create(
            content_type=self.ct,
            object_id=999,
            url="/other/",
            session_key="s2",
            timestamp=self.now,
        )

        result = get_period_stats(self.ct_str, self.object_id, period="week")
        self.assertEqual(result["total_views"], 1)


class ComparePeriodsTest(PeriodToolsTestBase):
    """Tests for compare_periods."""

    def test_invalid_content_type(self):
        result = compare_periods("invalid.model", 1)
        self.assertIn("error", result)

    def test_no_events_zero_growth(self):
        result = compare_periods(self.ct_str, self.object_id, period="week")
        self.assertEqual(result["current_period"]["total_views"], 0)
        self.assertEqual(result["previous_period"]["total_views"], 0)
        self.assertEqual(result["growth_rate"], 0.0)
        self.assertEqual(result["delta_views"], 0)

    def test_growth_with_current_only(self):
        self._create_event(days_ago=0, session_key="s1")
        self._create_event(days_ago=1, session_key="s2")

        result = compare_periods(self.ct_str, self.object_id, period="week")
        self.assertEqual(result["current_period"]["total_views"], 2)
        self.assertEqual(result["previous_period"]["total_views"], 0)
        self.assertEqual(result["growth_rate"], 100.0)
        self.assertEqual(result["delta_views"], 2)

    def test_growth_with_both_periods(self):
        # Current period (last 7 days)
        self._create_event(days_ago=0, session_key="s1")
        self._create_event(days_ago=1, session_key="s2")
        self._create_event(days_ago=2, session_key="s3")

        # Previous period (7-14 days ago)
        self._create_event(days_ago=8, session_key="s4")
        self._create_event(days_ago=9, session_key="s5")

        result = compare_periods(self.ct_str, self.object_id, period="week")
        self.assertEqual(result["current_period"]["total_views"], 3)
        self.assertEqual(result["previous_period"]["total_views"], 2)
        self.assertEqual(result["growth_rate"], 50.0)
        self.assertEqual(result["delta_views"], 1)

    def test_negative_growth(self):
        # Current period: 1 view
        self._create_event(days_ago=0, session_key="s1")

        # Previous period: 4 views
        self._create_event(days_ago=8, session_key="s2")
        self._create_event(days_ago=9, session_key="s3")
        self._create_event(days_ago=10, session_key="s4")
        self._create_event(days_ago=11, session_key="s5")

        result = compare_periods(self.ct_str, self.object_id, period="week")
        self.assertLess(result["growth_rate"], 0)
        self.assertLess(result["delta_views"], 0)

    def test_result_contains_expected_keys(self):
        result = compare_periods(self.ct_str, self.object_id, period="week")
        expected_keys = {
            "content_type",
            "object_id",
            "period",
            "current_period",
            "previous_period",
            "growth_rate",
            "delta_views",
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_current_period_has_date_keys(self):
        result = compare_periods(self.ct_str, self.object_id, period="week")
        self.assertIn("start_date", result["current_period"])
        self.assertIn("end_date", result["current_period"])
        self.assertIn("total_views", result["current_period"])

    def test_today_period_comparison(self):
        self._create_event(days_ago=0, session_key="s1")

        result = compare_periods(self.ct_str, self.object_id, period="today")
        self.assertEqual(result["period"], "today")
        self.assertGreaterEqual(result["current_period"]["total_views"], 1)
