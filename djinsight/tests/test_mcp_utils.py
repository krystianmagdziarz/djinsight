"""Tests for djinsight MCP utility functions."""

from datetime import datetime
from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from djinsight.mcp.utils import (
    classify_referrer,
    extract_domain,
    parse_content_type_str,
    parse_date_range,
    parse_user_agent_category,
)


class ParseContentTypeStrTest(TestCase):
    """Tests for parse_content_type_str."""

    def test_valid_content_type(self):
        ct = ContentType.objects.get(app_label="contenttypes", model="contenttype")
        result = parse_content_type_str("contenttypes.contenttype")
        self.assertEqual(result, ct)

    def test_nonexistent_model(self):
        self.assertIsNone(parse_content_type_str("myapp.nonexistent"))

    def test_none_input(self):
        self.assertIsNone(parse_content_type_str(None))

    def test_empty_string(self):
        self.assertIsNone(parse_content_type_str(""))

    def test_no_dot(self):
        self.assertIsNone(parse_content_type_str("contenttypes"))

    def test_too_many_dots(self):
        self.assertIsNone(parse_content_type_str("a.b.c"))

    def test_missing_model(self):
        self.assertIsNone(parse_content_type_str("contenttypes."))

    def test_missing_app_label(self):
        self.assertIsNone(parse_content_type_str(".contenttype"))

    def test_integer_input(self):
        self.assertIsNone(parse_content_type_str(123))


class ParseUserAgentCategoryTest(TestCase):
    """Tests for parse_user_agent_category."""

    def test_bot_googlebot(self):
        ua = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
        self.assertEqual(parse_user_agent_category(ua), "bot")

    def test_bot_crawler(self):
        self.assertEqual(parse_user_agent_category("Some crawler agent"), "bot")

    def test_bot_spider(self):
        self.assertEqual(parse_user_agent_category("MySpider/1.0"), "bot")

    def test_bot_baidu(self):
        self.assertEqual(parse_user_agent_category("Baiduspider/2.0"), "bot")

    def test_bot_yandex(self):
        self.assertEqual(parse_user_agent_category("YandexBot/3.0"), "bot")

    def test_tablet_ipad(self):
        ua = "Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X)"
        self.assertEqual(parse_user_agent_category(ua), "tablet")

    def test_tablet_kindle(self):
        ua = "Mozilla/5.0 (Linux; Android 4.4; Kindle Fire)"
        self.assertEqual(parse_user_agent_category(ua), "tablet")

    def test_mobile_iphone(self):
        ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)"
        self.assertEqual(parse_user_agent_category(ua), "mobile")

    def test_mobile_android(self):
        ua = "Mozilla/5.0 (Linux; Android 10; Mobile)"
        self.assertEqual(parse_user_agent_category(ua), "mobile")

    def test_mobile_windows_phone(self):
        ua = "Mozilla/5.0 (Windows Phone 10.0)"
        self.assertEqual(parse_user_agent_category(ua), "mobile")

    def test_desktop_windows(self):
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        self.assertEqual(parse_user_agent_category(ua), "desktop")

    def test_desktop_mac(self):
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        self.assertEqual(parse_user_agent_category(ua), "desktop")

    def test_desktop_linux(self):
        ua = "Mozilla/5.0 (X11; Linux x86_64)"
        self.assertEqual(parse_user_agent_category(ua), "desktop")

    def test_unknown_agent(self):
        self.assertEqual(parse_user_agent_category("SomeRandomAgent/1.0"), "unknown")

    def test_none_input(self):
        self.assertEqual(parse_user_agent_category(None), "unknown")

    def test_empty_string(self):
        self.assertEqual(parse_user_agent_category(""), "unknown")

    def test_bot_priority_over_desktop(self):
        """Bot patterns should match before desktop (e.g. Googlebot on Windows)."""
        ua = "Mozilla/5.0 (compatible; Googlebot/2.1) Windows NT"
        self.assertEqual(parse_user_agent_category(ua), "bot")


class ExtractDomainTest(TestCase):
    """Tests for extract_domain."""

    def test_simple_url(self):
        self.assertEqual(extract_domain("https://example.com/page"), "example.com")

    def test_strips_www(self):
        self.assertEqual(extract_domain("https://www.example.com/page"), "example.com")

    def test_with_port(self):
        self.assertEqual(extract_domain("https://example.com:8080/page"), "example.com")

    def test_subdomain(self):
        self.assertEqual(extract_domain("https://blog.example.com"), "blog.example.com")

    def test_none_returns_direct(self):
        self.assertEqual(extract_domain(None), "direct")

    def test_empty_string_returns_direct(self):
        self.assertEqual(extract_domain(""), "direct")

    def test_whitespace_returns_direct(self):
        self.assertEqual(extract_domain("   "), "direct")

    def test_no_scheme(self):
        # urlparse without scheme puts everything in path
        result = extract_domain("example.com/page")
        self.assertEqual(result, "direct")

    def test_http_scheme(self):
        self.assertEqual(extract_domain("http://example.com"), "example.com")


class ClassifyReferrerTest(TestCase):
    """Tests for classify_referrer."""

    def test_direct_none(self):
        self.assertEqual(classify_referrer(None), "direct")

    def test_direct_empty(self):
        self.assertEqual(classify_referrer(""), "direct")

    def test_search_google(self):
        self.assertEqual(
            classify_referrer("https://www.google.com/search?q=test"), "search"
        )

    def test_search_bing(self):
        self.assertEqual(classify_referrer("https://www.bing.com/search"), "search")

    def test_search_duckduckgo(self):
        self.assertEqual(classify_referrer("https://duckduckgo.com/?q=test"), "search")

    def test_search_ecosia(self):
        self.assertEqual(classify_referrer("https://www.ecosia.org/search"), "search")

    def test_social_facebook(self):
        self.assertEqual(
            classify_referrer("https://www.facebook.com/post/123"), "social"
        )

    def test_social_twitter(self):
        self.assertEqual(classify_referrer("https://twitter.com/user/status"), "social")

    def test_social_t_co(self):
        self.assertEqual(classify_referrer("https://t.co/abc123"), "social")

    def test_social_reddit(self):
        self.assertEqual(classify_referrer("https://www.reddit.com/r/django"), "social")

    def test_social_youtube(self):
        self.assertEqual(
            classify_referrer("https://www.youtube.com/watch?v=abc"), "social"
        )

    def test_social_linkedin(self):
        self.assertEqual(classify_referrer("https://www.linkedin.com/feed"), "social")

    def test_social_x_com(self):
        self.assertEqual(classify_referrer("https://x.com/user"), "social")

    def test_referral_unknown_site(self):
        self.assertEqual(classify_referrer("https://someblog.com/article"), "referral")

    def test_referral_another_site(self):
        self.assertEqual(classify_referrer("https://news.ycombinator.com"), "referral")


class ParseDateRangeTest(TestCase):
    """Tests for parse_date_range."""

    def test_today(self):
        start, end = parse_date_range("today")
        now = timezone.now()
        self.assertEqual(start.date(), now.date())
        self.assertEqual(start.hour, 0)
        self.assertEqual(start.minute, 0)

    def test_week(self):
        start, end = parse_date_range("week")
        now = timezone.now()
        expected_start_date = (now - timezone.timedelta(days=6)).date()
        self.assertEqual(start.date(), expected_start_date)

    def test_month(self):
        start, end = parse_date_range("month")
        now = timezone.now()
        expected_start_date = (now - timezone.timedelta(days=29)).date()
        self.assertEqual(start.date(), expected_start_date)

    def test_year(self):
        start, end = parse_date_range("year")
        now = timezone.now()
        expected_start_date = (now - timezone.timedelta(days=364)).date()
        self.assertEqual(start.date(), expected_start_date)

    def test_custom_valid(self):
        start, end = parse_date_range("custom", "2025-01-01", "2025-01-31")
        self.assertEqual(start.year, 2025)
        self.assertEqual(start.month, 1)
        self.assertEqual(start.day, 1)
        self.assertEqual(end.year, 2025)
        self.assertEqual(end.month, 1)
        self.assertEqual(end.day, 31)
        self.assertEqual(end.hour, 23)
        self.assertEqual(end.minute, 59)

    def test_custom_missing_start(self):
        with self.assertRaises(ValueError):
            parse_date_range("custom", end_date="2025-01-31")

    def test_custom_missing_end(self):
        with self.assertRaises(ValueError):
            parse_date_range("custom", start_date="2025-01-01")

    def test_custom_missing_both(self):
        with self.assertRaises(ValueError):
            parse_date_range("custom")

    def test_custom_invalid_format(self):
        with self.assertRaises(ValueError):
            parse_date_range("custom", "01-01-2025", "31-01-2025")

    def test_invalid_period(self):
        with self.assertRaises(ValueError):
            parse_date_range("invalid")

    def test_returns_aware_datetimes(self):
        start, end = parse_date_range("today")
        self.assertIsNotNone(start.tzinfo)
        self.assertIsNotNone(end.tzinfo)

    def test_custom_returns_aware_datetimes(self):
        start, end = parse_date_range("custom", "2025-06-01", "2025-06-30")
        self.assertIsNotNone(start.tzinfo)
        self.assertIsNotNone(end.tzinfo)
