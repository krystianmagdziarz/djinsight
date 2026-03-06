"""Tests for djinsight MCP behavior tools."""

from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from djinsight.mcp.tools.behavior import get_device_breakdown, get_hourly_pattern
from djinsight.models import PageViewEvent


class BehaviorToolsTestBase(TestCase):
    """Base class with shared setup for behavior tool tests."""

    @classmethod
    def setUpTestData(cls):
        cls.ct = ContentType.objects.get(app_label="contenttypes", model="contenttype")
        cls.ct_str = "contenttypes.contenttype"
        cls.object_id = cls.ct.pk

    def _create_event(self, user_agent="", hours_ago=0, object_id=None):
        """Helper to create a PageViewEvent."""
        return PageViewEvent.objects.create(
            content_type=self.ct,
            object_id=object_id or self.object_id,
            url="/test/",
            session_key="session-test",
            user_agent=user_agent,
            timestamp=timezone.now() - timedelta(hours=hours_ago),
        )


class GetDeviceBreakdownTest(BehaviorToolsTestBase):
    """Tests for get_device_breakdown."""

    def test_invalid_content_type(self):
        result = get_device_breakdown("invalid.model")
        self.assertIn("error", result)

    def test_empty_results(self):
        result = get_device_breakdown(self.ct_str, period="today")
        self.assertEqual(result["total_views"], 0)
        self.assertEqual(result["devices"], [])

    def test_desktop_chrome(self):
        self._create_event(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120"
        )
        result = get_device_breakdown(self.ct_str, period="today")
        self.assertEqual(result["total_views"], 1)
        devices = {d["device"]: d for d in result["devices"]}
        self.assertIn("desktop", devices)
        self.assertEqual(devices["desktop"]["views"], 1)
        self.assertEqual(devices["desktop"]["percentage"], 100.0)

    def test_mobile_iphone(self):
        self._create_event("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)")
        result = get_device_breakdown(self.ct_str, period="today")
        devices = {d["device"]: d for d in result["devices"]}
        self.assertIn("mobile", devices)

    def test_tablet_ipad(self):
        self._create_event("Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X)")
        result = get_device_breakdown(self.ct_str, period="today")
        devices = {d["device"]: d for d in result["devices"]}
        self.assertIn("tablet", devices)

    def test_bot_googlebot(self):
        self._create_event(
            "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
        )
        result = get_device_breakdown(self.ct_str, period="today")
        devices = {d["device"]: d for d in result["devices"]}
        self.assertIn("bot", devices)

    def test_multiple_device_types(self):
        self._create_event("Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120")
        self._create_event("Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121")
        self._create_event("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)")
        self._create_event("Mozilla/5.0 (compatible; Googlebot/2.1)")
        result = get_device_breakdown(self.ct_str, period="today")
        self.assertEqual(result["total_views"], 4)

        devices = {d["device"]: d for d in result["devices"]}
        self.assertEqual(devices["desktop"]["views"], 2)
        self.assertEqual(devices["desktop"]["percentage"], 50.0)
        self.assertEqual(devices["mobile"]["views"], 1)
        self.assertEqual(devices["mobile"]["percentage"], 25.0)
        self.assertEqual(devices["bot"]["views"], 1)

    def test_filter_by_object_id(self):
        other_id = self.object_id + 100
        self._create_event(
            "Mozilla/5.0 (Windows NT 10.0) Chrome/120", object_id=self.object_id
        )
        self._create_event(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0)", object_id=other_id
        )
        result = get_device_breakdown(
            self.ct_str, object_id=self.object_id, period="today"
        )
        self.assertEqual(result["total_views"], 1)
        self.assertEqual(result["object_id"], self.object_id)

    def test_period_filtering(self):
        # Event from 2 days ago should appear in week but not today
        self._create_event("Mozilla/5.0 (Windows NT 10.0) Chrome/120", hours_ago=48)
        result_today = get_device_breakdown(self.ct_str, period="today")
        result_week = get_device_breakdown(self.ct_str, period="week")
        self.assertEqual(result_today["total_views"], 0)
        self.assertEqual(result_week["total_views"], 1)

    def test_response_structure(self):
        self._create_event("Mozilla/5.0 (Windows NT 10.0) Chrome/120")
        result = get_device_breakdown(self.ct_str, period="month")
        self.assertEqual(result["content_type"], self.ct_str)
        self.assertEqual(result["period"], "month")
        self.assertIn("total_views", result)
        self.assertIn("devices", result)
        for device in result["devices"]:
            self.assertIn("device", device)
            self.assertIn("views", device)
            self.assertIn("percentage", device)


class GetHourlyPatternTest(BehaviorToolsTestBase):
    """Tests for get_hourly_pattern."""

    def test_invalid_content_type(self):
        result = get_hourly_pattern("invalid.model")
        self.assertIn("error", result)

    def test_empty_results(self):
        result = get_hourly_pattern(self.ct_str, period="today")
        self.assertEqual(result["total_views"], 0)
        self.assertEqual(len(result["hours"]), 24)
        self.assertEqual(result["peak_hour"], "00:00")

    def test_24_hours_returned(self):
        self._create_event("Mozilla/5.0 Chrome/120")
        result = get_hourly_pattern(self.ct_str, period="today")
        self.assertEqual(len(result["hours"]), 24)
        hours_seen = [h["hour"] for h in result["hours"]]
        self.assertEqual(hours_seen, list(range(24)))

    def test_hour_labels_format(self):
        result = get_hourly_pattern(self.ct_str, period="today")
        for entry in result["hours"]:
            self.assertRegex(entry["label"], r"^\d{2}:00$")
        self.assertEqual(result["hours"][0]["label"], "00:00")
        self.assertEqual(result["hours"][9]["label"], "09:00")
        self.assertEqual(result["hours"][23]["label"], "23:00")

    def test_peak_hour_calculation(self):
        now = timezone.now()
        # Create 3 events at current hour and 1 at a different hour
        for _ in range(3):
            self._create_event("Mozilla/5.0 Chrome/120", hours_ago=0)

        # Create 1 event a few hours ago (ensuring a different hour)
        self._create_event("Mozilla/5.0 Chrome/120", hours_ago=3)

        result = get_hourly_pattern(self.ct_str, period="today")
        expected_peak = f"{now.hour:02d}:00"
        self.assertEqual(result["peak_hour"], expected_peak)

    def test_views_counted_by_hour(self):
        now = timezone.now()
        self._create_event("Mozilla/5.0 Chrome/120", hours_ago=0)
        self._create_event("Mozilla/5.0 Chrome/121", hours_ago=0)

        result = get_hourly_pattern(self.ct_str, period="today")
        current_hour_entry = result["hours"][now.hour]
        self.assertEqual(current_hour_entry["views"], 2)

    def test_filter_by_object_id(self):
        other_id = self.object_id + 100
        self._create_event("Mozilla/5.0 Chrome/120", object_id=self.object_id)
        self._create_event("Mozilla/5.0 Chrome/120", object_id=other_id)

        result = get_hourly_pattern(
            self.ct_str, object_id=self.object_id, period="today"
        )
        self.assertEqual(result["total_views"], 1)
        self.assertEqual(result["object_id"], self.object_id)

    def test_period_filtering(self):
        self._create_event("Mozilla/5.0 Chrome/120", hours_ago=48)
        result_today = get_hourly_pattern(self.ct_str, period="today")
        result_week = get_hourly_pattern(self.ct_str, period="week")
        self.assertEqual(result_today["total_views"], 0)
        self.assertEqual(result_week["total_views"], 1)

    def test_response_structure(self):
        self._create_event("Mozilla/5.0 Chrome/120")
        result = get_hourly_pattern(self.ct_str, period="week")
        self.assertEqual(result["content_type"], self.ct_str)
        self.assertEqual(result["period"], "week")
        self.assertIn("total_views", result)
        self.assertIn("peak_hour", result)
        self.assertIn("hours", result)
        for hour_entry in result["hours"]:
            self.assertIn("hour", hour_entry)
            self.assertIn("label", hour_entry)
            self.assertIn("views", hour_entry)

    def test_events_at_various_hours(self):
        """Events at different hours are counted in the correct buckets."""
        now = timezone.now()
        # Create events at known hour offsets
        self._create_event("Mozilla/5.0 Chrome/120", hours_ago=1)
        self._create_event("Mozilla/5.0 Chrome/120", hours_ago=2)

        result = get_hourly_pattern(self.ct_str, period="today")
        total_counted = sum(h["views"] for h in result["hours"])
        self.assertEqual(total_counted, result["total_views"])
