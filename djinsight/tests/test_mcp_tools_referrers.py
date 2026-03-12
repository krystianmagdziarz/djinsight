"""Tests for djinsight MCP referrer tools."""

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from djinsight.mcp.tools.referrers import get_referrer_stats, get_traffic_sources
from djinsight.models import PageViewEvent, PageViewStatistics


class ReferrerToolsTestBase(TestCase):
    """Base class with shared setup for referrer tool tests."""

    def setUp(self):
        self.ct = ContentType.objects.get_for_model(PageViewStatistics)
        self.ct_str = f"{self.ct.app_label}.{self.ct.model}"
        now = timezone.now()

        # Google search referrer
        PageViewEvent.objects.create(
            content_type=self.ct,
            object_id=1,
            url="/page/1",
            session_key="sess1",
            referrer="https://www.google.com/search?q=test",
            timestamp=now,
        )
        # Another Google hit
        PageViewEvent.objects.create(
            content_type=self.ct,
            object_id=1,
            url="/page/1",
            session_key="sess2",
            referrer="https://www.google.com/search?q=other",
            timestamp=now,
        )
        # Facebook social referrer
        PageViewEvent.objects.create(
            content_type=self.ct,
            object_id=1,
            url="/page/1",
            session_key="sess3",
            referrer="https://www.facebook.com/post/123",
            timestamp=now,
        )
        # Direct (empty referrer)
        PageViewEvent.objects.create(
            content_type=self.ct,
            object_id=1,
            url="/page/1",
            session_key="sess4",
            referrer="",
            timestamp=now,
        )
        # Direct (null referrer)
        PageViewEvent.objects.create(
            content_type=self.ct,
            object_id=1,
            url="/page/1",
            session_key="sess5",
            referrer=None,
            timestamp=now,
        )
        # Random blog referral
        PageViewEvent.objects.create(
            content_type=self.ct,
            object_id=1,
            url="/page/1",
            session_key="sess6",
            referrer="https://someblog.com/article",
            timestamp=now,
        )
        # Event for a different object_id
        PageViewEvent.objects.create(
            content_type=self.ct,
            object_id=2,
            url="/page/2",
            session_key="sess7",
            referrer="https://reddit.com/r/django",
            timestamp=now,
        )


class GetReferrerStatsTest(ReferrerToolsTestBase):
    """Tests for get_referrer_stats."""

    def test_groups_by_domain(self):
        result = get_referrer_stats(self.ct_str)
        domains = {r["domain"]: r["views"] for r in result["referrers"]}
        self.assertEqual(domains["google.com"], 2)
        self.assertEqual(domains["facebook.com"], 1)
        self.assertEqual(domains["someblog.com"], 1)

    def test_direct_counted(self):
        result = get_referrer_stats(self.ct_str)
        domains = {r["domain"]: r["views"] for r in result["referrers"]}
        # Two direct hits: empty string + None
        self.assertEqual(domains["direct"], 2)

    def test_total_referrals(self):
        result = get_referrer_stats(self.ct_str)
        # 6 events for object_id=1 + 1 for object_id=2 = 7
        self.assertEqual(result["total_referrals"], 7)

    def test_filter_by_object_id(self):
        result = get_referrer_stats(self.ct_str, object_id=2)
        self.assertEqual(result["total_referrals"], 1)
        self.assertEqual(result["referrers"][0]["domain"], "reddit.com")

    def test_limit(self):
        result = get_referrer_stats(self.ct_str, limit=2)
        self.assertLessEqual(len(result["referrers"]), 2)

    def test_invalid_content_type(self):
        result = get_referrer_stats("nonexistent.model")
        self.assertIn("error", result)

    def test_sorted_by_views_desc(self):
        result = get_referrer_stats(self.ct_str)
        views = [r["views"] for r in result["referrers"]]
        self.assertEqual(views, sorted(views, reverse=True))

    def test_response_structure(self):
        result = get_referrer_stats(self.ct_str, object_id=1, period="month")
        self.assertEqual(result["content_type"], self.ct_str)
        self.assertEqual(result["object_id"], 1)
        self.assertEqual(result["period"], "month")
        self.assertIn("total_referrals", result)
        self.assertIn("referrers", result)
        for ref in result["referrers"]:
            self.assertIn("domain", ref)
            self.assertIn("views", ref)


class GetTrafficSourcesTest(ReferrerToolsTestBase):
    """Tests for get_traffic_sources."""

    def test_classifies_sources(self):
        result = get_traffic_sources(self.ct_str, object_id=1)
        sources = {s["source"]: s["views"] for s in result["sources"]}
        self.assertEqual(sources["search"], 2)  # 2x google
        self.assertEqual(sources["social"], 1)  # facebook
        self.assertEqual(sources["direct"], 2)  # empty + null
        self.assertEqual(sources["referral"], 1)  # someblog

    def test_total_views(self):
        result = get_traffic_sources(self.ct_str, object_id=1)
        self.assertEqual(result["total_views"], 6)

    def test_percentages_sum_to_100(self):
        result = get_traffic_sources(self.ct_str, object_id=1)
        total_pct = sum(s["percentage"] for s in result["sources"])
        self.assertAlmostEqual(total_pct, 100.0, places=0)

    def test_percentage_calculation(self):
        result = get_traffic_sources(self.ct_str, object_id=1)
        sources = {s["source"]: s["percentage"] for s in result["sources"]}
        # search = 2/6 = 33.3%
        self.assertAlmostEqual(sources["search"], 33.3, places=1)
        # direct = 2/6 = 33.3%
        self.assertAlmostEqual(sources["direct"], 33.3, places=1)

    def test_filter_by_object_id(self):
        result = get_traffic_sources(self.ct_str, object_id=2)
        self.assertEqual(result["total_views"], 1)
        sources = {s["source"]: s["views"] for s in result["sources"]}
        self.assertEqual(sources["social"], 1)  # reddit

    def test_invalid_content_type(self):
        result = get_traffic_sources("nonexistent.model")
        self.assertIn("error", result)

    def test_response_structure(self):
        result = get_traffic_sources(self.ct_str, object_id=1, period="month")
        self.assertEqual(result["content_type"], self.ct_str)
        self.assertEqual(result["object_id"], 1)
        self.assertEqual(result["period"], "month")
        self.assertIn("total_views", result)
        self.assertIn("sources", result)
        for src in result["sources"]:
            self.assertIn("source", src)
            self.assertIn("views", src)
            self.assertIn("percentage", src)

    def test_all_sources_without_object_filter(self):
        result = get_traffic_sources(self.ct_str)
        self.assertEqual(result["total_views"], 7)
