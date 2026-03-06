"""Utility functions for the djinsight MCP server."""

import re
from datetime import datetime, timedelta
from urllib.parse import urlparse

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone


def parse_content_type_str(content_type_str):
    """Parse 'app_label.model' string into a ContentType instance.

    Returns None if the string is invalid or the ContentType doesn't exist.
    """
    if not content_type_str or not isinstance(content_type_str, str):
        return None

    parts = content_type_str.split(".")
    if len(parts) != 2:
        return None

    app_label, model = parts
    if not app_label or not model:
        return None

    try:
        return ContentType.objects.get(app_label=app_label, model=model)
    except ContentType.DoesNotExist:
        return None


def parse_user_agent_category(user_agent):
    """Classify a user agent string into a device category.

    Returns one of: 'bot', 'tablet', 'mobile', 'desktop', 'unknown'.
    """
    if not user_agent or not isinstance(user_agent, str):
        return "unknown"

    ua = user_agent.lower()

    if re.search(r"bot|crawl|spider|slurp|yahoo|baidu|yandex|duckduck", ua):
        return "bot"

    if re.search(r"ipad|tablet|kindle|silk|playbook", ua):
        return "tablet"

    if re.search(
        r"iphone|android.*mobile|windows phone|blackberry|opera mini|opera mobi", ua
    ):
        return "mobile"

    if re.search(r"windows|macintosh|linux|x11", ua):
        return "desktop"

    return "unknown"


def extract_domain(url):
    """Extract the domain from a URL, stripping 'www.' prefix.

    Returns 'direct' for empty or None URLs.
    """
    if not url or not isinstance(url, str):
        return "direct"

    url = url.strip()
    if not url:
        return "direct"

    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return "direct"
        if hostname.startswith("www."):
            hostname = hostname[4:]
        return hostname
    except Exception:
        return "direct"


SEARCH_DOMAINS = {
    "google",
    "bing",
    "yahoo",
    "duckduckgo",
    "baidu",
    "yandex",
    "ecosia",
    "ask",
    "aol",
    "startpage",
}

SOCIAL_DOMAINS = {
    "facebook.com",
    "twitter.com",
    "t.co",
    "x.com",
    "instagram.com",
    "linkedin.com",
    "reddit.com",
    "youtube.com",
    "tiktok.com",
    "pinterest.com",
    "tumblr.com",
    "mastodon.social",
}


def classify_referrer(referrer):
    """Classify a referrer URL into a traffic source category.

    Returns one of: 'direct', 'search', 'social', 'referral'.
    """
    domain = extract_domain(referrer)
    if domain == "direct":
        return "direct"

    # Check search engines - match if domain contains a search engine name
    domain_lower = domain.lower()
    for search_domain in SEARCH_DOMAINS:
        if search_domain in domain_lower:
            return "search"

    # Check social networks - match if domain ends with a social domain
    for social_domain in SOCIAL_DOMAINS:
        if domain_lower == social_domain or domain_lower.endswith("." + social_domain):
            return "social"

    return "referral"


def parse_date_range(period, start_date=None, end_date=None):
    """Parse a period string into a (start_datetime, end_datetime) tuple.

    Args:
        period: One of 'today', 'week', 'month', 'year', 'custom'.
        start_date: Required for 'custom' period, format 'YYYY-MM-DD'.
        end_date: Required for 'custom' period, format 'YYYY-MM-DD'.

    Returns:
        Tuple of (start_datetime, end_datetime) as timezone-aware datetimes.

    Raises:
        ValueError: If period is invalid or custom dates are missing/malformed.
    """
    now = timezone.now()
    end = now

    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start = (now - timedelta(days=6)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    elif period == "month":
        start = (now - timedelta(days=29)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    elif period == "year":
        start = (now - timedelta(days=364)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    elif period == "custom":
        if not start_date or not end_date:
            raise ValueError("start_date and end_date are required for custom period")
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid date format. Use YYYY-MM-DD: {e}")

        start = timezone.make_aware(
            start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        )
        end = timezone.make_aware(
            end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        )
    else:
        raise ValueError(
            f"Invalid period: {period}. Must be one of: today, week, month, year, custom"
        )

    return (start, end)
