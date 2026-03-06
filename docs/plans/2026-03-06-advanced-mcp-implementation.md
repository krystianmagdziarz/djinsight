# Advanced MCP Server Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the custom HTTP+Node.js MCP with a native Python MCP server (13 analytics tools) using the `mcp` SDK.

**Architecture:** FastMCP server with stdio transport. Tools organized in `djinsight/mcp/tools/` modules. Django ORM access via `django.setup()` in `__main__.py`. User agent parsing with lightweight regex (no external deps).

**Tech Stack:** Python `mcp` SDK (FastMCP), Django ORM, regex-based UA parsing

---

### Task 1: Add `mcp` to optional dependencies

**Files:**
- Modify: `pyproject.toml:55-76`

**Step 1: Add mcp optional dependency group**

In `pyproject.toml`, add a new optional dependency group after the existing ones:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=6.0",
    "pytest-django>=4.0",
    "pytest-cov>=3.0",
    "black>=22.0",
    "flake8>=4.0",
    "isort>=5.0",
    "mypy>=0.900",
    "factory-boy>=3.0",
]
docs = [
    "sphinx>=4.0",
    "sphinx-rtd-theme>=1.0",
]
test = [
    "pytest>=6.0",
    "pytest-django>=4.0",
    "pytest-cov>=3.0",
    "factory-boy>=3.0",
    "coverage>=6.0",
]
mcp = [
    "mcp>=1.0.0",
]
```

Also update `[tool.setuptools]` packages to include subpackages:

```toml
[tool.setuptools.packages.find]
include = ["djinsight*"]
```

Replace the existing `[tool.setuptools]` block (lines ~85-96).

**Step 2: Install mcp in dev environment**

Run: `pip install -e ".[mcp,dev]"`

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "feat: add mcp optional dependency group"
```

---

### Task 2: Create MCP utils module

**Files:**
- Create: `djinsight/mcp/utils.py`
- Test: `djinsight/tests/test_mcp_utils.py`

**Step 1: Write tests for utils**

```python
"""Tests for MCP utility functions."""
from datetime import date, datetime, timedelta

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
from djinsight.models import PageViewStatistics


class ParseContentTypeStrTest(TestCase):
    def test_valid_content_type(self):
        ct = ContentType.objects.get_for_model(PageViewStatistics)
        result = parse_content_type_str(f"{ct.app_label}.{ct.model}")
        self.assertEqual(result, ct)

    def test_invalid_format(self):
        self.assertIsNone(parse_content_type_str("invalid"))

    def test_nonexistent_model(self):
        self.assertIsNone(parse_content_type_str("fake.model"))


class ParseUserAgentCategoryTest(TestCase):
    def test_mobile_android(self):
        ua = "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Mobile Safari/537.36"
        self.assertEqual(parse_user_agent_category(ua), "mobile")

    def test_mobile_iphone(self):
        ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0) AppleWebKit/605.1.15 Mobile/15E148"
        self.assertEqual(parse_user_agent_category(ua), "mobile")

    def test_tablet_ipad(self):
        ua = "Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15"
        self.assertEqual(parse_user_agent_category(ua), "tablet")

    def test_desktop_chrome(self):
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/91.0"
        self.assertEqual(parse_user_agent_category(ua), "desktop")

    def test_bot(self):
        ua = "Googlebot/2.1 (+http://www.google.com/bot.html)"
        self.assertEqual(parse_user_agent_category(ua), "bot")

    def test_empty(self):
        self.assertEqual(parse_user_agent_category(""), "unknown")

    def test_none(self):
        self.assertEqual(parse_user_agent_category(None), "unknown")


class ExtractDomainTest(TestCase):
    def test_full_url(self):
        self.assertEqual(extract_domain("https://www.example.com/path"), "example.com")

    def test_with_www(self):
        self.assertEqual(extract_domain("https://www.google.com"), "google.com")

    def test_without_www(self):
        self.assertEqual(extract_domain("https://example.com"), "example.com")

    def test_empty(self):
        self.assertEqual(extract_domain(""), "direct")

    def test_none(self):
        self.assertEqual(extract_domain(None), "direct")


class ClassifyReferrerTest(TestCase):
    def test_search_google(self):
        self.assertEqual(classify_referrer("https://www.google.com/search?q=test"), "search")

    def test_social_facebook(self):
        self.assertEqual(classify_referrer("https://www.facebook.com/post/123"), "social")

    def test_social_twitter(self):
        self.assertEqual(classify_referrer("https://t.co/abc123"), "social")

    def test_direct(self):
        self.assertEqual(classify_referrer(""), "direct")

    def test_referral(self):
        self.assertEqual(classify_referrer("https://some-blog.com/article"), "referral")


class ParseDateRangeTest(TestCase):
    def test_today(self):
        start, end = parse_date_range("today")
        self.assertEqual(start.date(), timezone.now().date())

    def test_week(self):
        start, end = parse_date_range("week")
        self.assertEqual((end - start).days, 6)

    def test_month(self):
        start, end = parse_date_range("month")
        self.assertEqual((end - start).days, 29)

    def test_year(self):
        start, end = parse_date_range("year")
        self.assertEqual((end - start).days, 364)

    def test_custom(self):
        start, end = parse_date_range("custom", "2026-01-01", "2026-01-31")
        self.assertEqual(start.date(), date(2026, 1, 1))
        self.assertEqual(end.date(), date(2026, 1, 31))

    def test_invalid_period(self):
        with self.assertRaises(ValueError):
            parse_date_range("invalid")
```

**Step 2: Run tests to verify they fail**

Run: `pytest djinsight/tests/test_mcp_utils.py -v`
Expected: ImportError

**Step 3: Implement utils**

```python
"""Utility functions for MCP tools."""
import re
from datetime import date, datetime, timedelta
from typing import Optional, Tuple
from urllib.parse import urlparse

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone


def parse_content_type_str(content_type_str: str) -> Optional[ContentType]:
    """Parse 'app_label.model' string into ContentType object."""
    try:
        app_label, model = content_type_str.split(".")
        return ContentType.objects.get(app_label=app_label, model=model.lower())
    except (ValueError, ContentType.DoesNotExist):
        return None


def parse_user_agent_category(user_agent: Optional[str]) -> str:
    """Classify user agent into: mobile, tablet, desktop, bot, unknown."""
    if not user_agent:
        return "unknown"

    ua = user_agent.lower()

    bot_patterns = r"bot|crawl|spider|slurp|yahoo|baidu|yandex|duckduck"
    if re.search(bot_patterns, ua):
        return "bot"

    if re.search(r"ipad|tablet|kindle|silk|playbook", ua):
        return "tablet"

    if re.search(r"iphone|android.*mobile|windows phone|blackberry|opera mini|opera mobi", ua):
        return "mobile"

    if re.search(r"windows|macintosh|linux|x11", ua):
        return "desktop"

    return "unknown"


def extract_domain(url: Optional[str]) -> str:
    """Extract domain from URL, stripping www prefix. Returns 'direct' for empty."""
    if not url:
        return "direct"
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        domain = domain.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain or "direct"
    except Exception:
        return "direct"


SEARCH_DOMAINS = {
    "google", "bing", "yahoo", "duckduckgo", "baidu", "yandex",
    "ecosia", "ask", "aol", "startpage",
}

SOCIAL_DOMAINS = {
    "facebook.com", "twitter.com", "t.co", "x.com", "instagram.com",
    "linkedin.com", "reddit.com", "youtube.com", "tiktok.com",
    "pinterest.com", "tumblr.com", "mastodon.social",
}


def classify_referrer(referrer: Optional[str]) -> str:
    """Classify referrer into: direct, search, social, referral."""
    if not referrer:
        return "direct"

    domain = extract_domain(referrer)
    if domain == "direct":
        return "direct"

    base_domain = ".".join(domain.rsplit(".", 2)[-2:]) if "." in domain else domain

    for search in SEARCH_DOMAINS:
        if search in base_domain:
            return "search"

    if base_domain in SOCIAL_DOMAINS or domain in SOCIAL_DOMAINS:
        return "social"

    return "referral"


def parse_date_range(
    period: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Tuple[datetime, datetime]:
    """Parse period string into start/end datetime tuple."""
    now = timezone.now()
    end = now

    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        start = (now - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "year":
        start = (now - timedelta(days=364)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "custom":
        if not start_date or not end_date:
            raise ValueError("custom period requires start_date and end_date")
        start = timezone.make_aware(datetime.strptime(start_date, "%Y-%m-%d"))
        end = timezone.make_aware(
            datetime.strptime(end_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
        )
    else:
        raise ValueError(f"Invalid period: {period}. Use: today, week, month, year, custom")

    return start, end
```

**Step 4: Run tests to verify they pass**

Run: `pytest djinsight/tests/test_mcp_utils.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add djinsight/mcp/utils.py djinsight/tests/test_mcp_utils.py
git commit -m "feat: add MCP utility functions (content type parsing, UA classification, referrer classification, date ranges)"
```

---

### Task 3: Create basic tools module

**Files:**
- Create: `djinsight/mcp/tools/__init__.py`
- Create: `djinsight/mcp/tools/basic.py`
- Test: `djinsight/tests/test_mcp_tools_basic.py`

**Step 1: Write tests**

```python
"""Tests for basic MCP tools."""
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from djinsight.mcp.tools.basic import get_page_stats, get_top_pages, list_tracked_models
from djinsight.models import ContentTypeRegistry, PageViewStatistics


class GetPageStatsTest(TestCase):
    def setUp(self):
        self.ct = ContentType.objects.get_for_model(PageViewStatistics)
        self.ct_str = f"{self.ct.app_label}.{self.ct.model}"

    def test_returns_stats_for_existing_object(self):
        PageViewStatistics.objects.create(
            content_type=self.ct, object_id=1,
            total_views=50, unique_views=30,
            first_viewed_at=timezone.now(), last_viewed_at=timezone.now(),
        )
        result = get_page_stats(self.ct_str, 1)
        self.assertEqual(result["total_views"], 50)
        self.assertEqual(result["unique_views"], 30)

    def test_returns_zeros_for_nonexistent(self):
        result = get_page_stats(self.ct_str, 999)
        self.assertEqual(result["total_views"], 0)

    def test_invalid_content_type(self):
        result = get_page_stats("fake.model", 1)
        self.assertIn("error", result)


class GetTopPagesTest(TestCase):
    def setUp(self):
        self.ct = ContentType.objects.get_for_model(PageViewStatistics)
        self.ct_str = f"{self.ct.app_label}.{self.ct.model}"
        for i in range(5):
            PageViewStatistics.objects.create(
                content_type=self.ct, object_id=i + 1,
                total_views=(i + 1) * 10, unique_views=(i + 1) * 5,
            )

    def test_returns_top_pages_sorted(self):
        result = get_top_pages(self.ct_str, limit=3)
        self.assertEqual(len(result["results"]), 3)
        self.assertEqual(result["results"][0]["total_views"], 50)

    def test_limit_default(self):
        result = get_top_pages(self.ct_str)
        self.assertEqual(len(result["results"]), 5)


class ListTrackedModelsTest(TestCase):
    def test_returns_registered_models(self):
        ContentTypeRegistry.register(PageViewStatistics)
        result = list_tracked_models()
        self.assertEqual(len(result["tracked_models"]), 1)

    def test_empty_when_none_registered(self):
        result = list_tracked_models()
        self.assertEqual(len(result["tracked_models"]), 0)
```

**Step 2: Run tests to verify they fail**

Run: `pytest djinsight/tests/test_mcp_tools_basic.py -v`
Expected: ImportError

**Step 3: Create `djinsight/mcp/tools/__init__.py`**

```python
```

(Empty file)

**Step 4: Implement basic tools**

```python
"""Basic MCP tools: get_page_stats, get_top_pages, list_tracked_models."""
from typing import Any, Dict, Optional

from django.contrib.contenttypes.models import ContentType

from djinsight.mcp.utils import parse_content_type_str
from djinsight.models import ContentTypeRegistry, PageViewStatistics


def get_page_stats(content_type: str, object_id: int) -> Dict[str, Any]:
    """Get page view statistics for a specific object.

    Args:
        content_type: Content type in format 'app_label.model' (e.g., 'blog.post')
        object_id: The object's primary key
    """
    ct = parse_content_type_str(content_type)
    if not ct:
        return {"error": f"Invalid content type: {content_type}"}

    obj_str = None
    try:
        model_class = ct.model_class()
        obj = model_class.objects.get(pk=object_id)
        obj_str = str(obj)
    except Exception:
        pass

    stats = PageViewStatistics.objects.filter(
        content_type=ct, object_id=object_id
    ).first()

    if not stats:
        return {
            "content_type": content_type,
            "object_id": object_id,
            "object": obj_str,
            "total_views": 0,
            "unique_views": 0,
            "first_viewed_at": None,
            "last_viewed_at": None,
        }

    return {
        "content_type": content_type,
        "object_id": object_id,
        "object": obj_str,
        "total_views": stats.total_views,
        "unique_views": stats.unique_views,
        "first_viewed_at": stats.first_viewed_at.isoformat() if stats.first_viewed_at else None,
        "last_viewed_at": stats.last_viewed_at.isoformat() if stats.last_viewed_at else None,
    }


def get_top_pages(
    content_type: str,
    limit: int = 10,
    metric: str = "total_views",
) -> Dict[str, Any]:
    """Get top performing pages by views.

    Args:
        content_type: Content type in format 'app_label.model'
        limit: Number of results (default: 10)
        metric: Sort by 'total_views' or 'unique_views'
    """
    ct = parse_content_type_str(content_type)
    if not ct:
        return {"error": f"Invalid content type: {content_type}"}

    if metric not in ("total_views", "unique_views"):
        metric = "total_views"

    stats = PageViewStatistics.objects.filter(content_type=ct).order_by(f"-{metric}")[:limit]

    model_class = ct.model_class()
    object_ids = [s.object_id for s in stats]
    objects_dict = {}
    try:
        objects = model_class.objects.filter(pk__in=object_ids)
        objects_dict = {obj.pk: str(obj) for obj in objects}
    except Exception:
        pass

    return {
        "content_type": content_type,
        "metric": metric,
        "results": [
            {
                "object_id": s.object_id,
                "object": objects_dict.get(s.object_id),
                "total_views": s.total_views,
                "unique_views": s.unique_views,
                "last_viewed_at": s.last_viewed_at.isoformat() if s.last_viewed_at else None,
            }
            for s in stats
        ],
    }


def list_tracked_models() -> Dict[str, Any]:
    """List all content types that are being tracked."""
    registries = ContentTypeRegistry.objects.filter(enabled=True).select_related("content_type")

    return {
        "tracked_models": [
            {
                "app_label": r.content_type.app_label,
                "model": r.content_type.model,
                "content_type": f"{r.content_type.app_label}.{r.content_type.model}",
                "track_anonymous": r.track_anonymous,
                "track_authenticated": r.track_authenticated,
            }
            for r in registries
        ]
    }
```

**Step 5: Run tests**

Run: `pytest djinsight/tests/test_mcp_tools_basic.py -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add djinsight/mcp/tools/__init__.py djinsight/mcp/tools/basic.py djinsight/tests/test_mcp_tools_basic.py
git commit -m "feat: add basic MCP tools (get_page_stats, get_top_pages, list_tracked_models)"
```

---

### Task 4: Create periods tools module

**Files:**
- Create: `djinsight/mcp/tools/periods.py`
- Test: `djinsight/tests/test_mcp_tools_periods.py`

**Step 1: Write tests**

```python
"""Tests for period-based MCP tools."""
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from djinsight.mcp.tools.periods import compare_periods, get_period_stats
from djinsight.models import PageViewEvent, PageViewStatistics


class GetPeriodStatsTest(TestCase):
    def setUp(self):
        self.ct = ContentType.objects.get_for_model(PageViewStatistics)
        self.ct_str = f"{self.ct.app_label}.{self.ct.model}"
        self.stats = PageViewStatistics.objects.create(
            content_type=self.ct, object_id=1, total_views=100, unique_views=50,
        )
        now = timezone.now()
        for i in range(5):
            PageViewEvent.objects.create(
                content_type=self.ct, object_id=1, url="/test/",
                session_key=f"session-{i}", timestamp=now - timedelta(hours=i),
            )

    def test_today_stats(self):
        result = get_period_stats(self.ct_str, 1, "today")
        self.assertIn("total_views", result)
        self.assertEqual(result["total_views"], 5)

    def test_invalid_content_type(self):
        result = get_period_stats("fake.model", 1, "today")
        self.assertIn("error", result)


class ComparePeriodsTest(TestCase):
    def setUp(self):
        self.ct = ContentType.objects.get_for_model(PageViewStatistics)
        self.ct_str = f"{self.ct.app_label}.{self.ct.model}"
        now = timezone.now()
        # This week: 10 events
        for i in range(10):
            PageViewEvent.objects.create(
                content_type=self.ct, object_id=1, url="/test/",
                session_key=f"s-{i}", timestamp=now - timedelta(hours=i),
            )
        # Last week: 5 events
        for i in range(5):
            PageViewEvent.objects.create(
                content_type=self.ct, object_id=1, url="/test/",
                session_key=f"prev-{i}", timestamp=now - timedelta(days=8, hours=i),
            )

    def test_compare_returns_growth(self):
        result = compare_periods(self.ct_str, 1, "week")
        self.assertIn("current_period", result)
        self.assertIn("previous_period", result)
        self.assertIn("growth_rate", result)
        self.assertGreater(result["current_period"]["total_views"], 0)

    def test_invalid_content_type(self):
        result = compare_periods("fake.model", 1, "week")
        self.assertIn("error", result)
```

**Step 2: Run tests to verify they fail**

Run: `pytest djinsight/tests/test_mcp_tools_periods.py -v`

**Step 3: Implement periods tools**

```python
"""Period-based MCP tools: get_period_stats, compare_periods."""
from datetime import timedelta
from typing import Any, Dict, Optional

from django.db.models import Count

from djinsight.mcp.utils import parse_content_type_str, parse_date_range
from djinsight.models import PageViewEvent


def get_period_stats(
    content_type: str,
    object_id: int,
    period: str = "week",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Get view statistics for a specific time period.

    Args:
        content_type: Content type in format 'app_label.model'
        object_id: The object's primary key
        period: One of 'today', 'week', 'month', 'year', 'custom'
        start_date: Start date for custom period (YYYY-MM-DD)
        end_date: End date for custom period (YYYY-MM-DD)
    """
    ct = parse_content_type_str(content_type)
    if not ct:
        return {"error": f"Invalid content type: {content_type}"}

    try:
        start, end = parse_date_range(period, start_date, end_date)
    except ValueError as e:
        return {"error": str(e)}

    events = PageViewEvent.objects.filter(
        content_type=ct, object_id=object_id,
        timestamp__gte=start, timestamp__lte=end,
    )

    total_views = events.count()
    unique_views = events.values("session_key").distinct().count()

    # Daily breakdown
    daily = (
        events.extra({"day": "date(timestamp)"})
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )

    return {
        "content_type": content_type,
        "object_id": object_id,
        "period": period,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "total_views": total_views,
        "unique_views": unique_views,
        "daily_breakdown": [
            {"date": str(d["day"]), "views": d["count"]} for d in daily
        ],
    }


def compare_periods(
    content_type: str,
    object_id: int,
    period: str = "week",
) -> Dict[str, Any]:
    """Compare current period with previous period of same length.

    Args:
        content_type: Content type in format 'app_label.model'
        object_id: The object's primary key
        period: One of 'today', 'week', 'month', 'year'
    """
    ct = parse_content_type_str(content_type)
    if not ct:
        return {"error": f"Invalid content type: {content_type}"}

    try:
        current_start, current_end = parse_date_range(period)
    except ValueError as e:
        return {"error": str(e)}

    duration = current_end - current_start
    previous_end = current_start - timedelta(seconds=1)
    previous_start = previous_end - duration

    def count_views(start, end):
        qs = PageViewEvent.objects.filter(
            content_type=ct, object_id=object_id,
            timestamp__gte=start, timestamp__lte=end,
        )
        return {
            "total_views": qs.count(),
            "unique_views": qs.values("session_key").distinct().count(),
        }

    current = count_views(current_start, current_end)
    previous = count_views(previous_start, previous_end)

    prev_total = previous["total_views"]
    curr_total = current["total_views"]

    if prev_total > 0:
        growth_rate = round(((curr_total - prev_total) / prev_total) * 100, 1)
    elif curr_total > 0:
        growth_rate = 100.0
    else:
        growth_rate = 0.0

    return {
        "content_type": content_type,
        "object_id": object_id,
        "period": period,
        "current_period": {
            "start": current_start.isoformat(),
            "end": current_end.isoformat(),
            **current,
        },
        "previous_period": {
            "start": previous_start.isoformat(),
            "end": previous_end.isoformat(),
            **previous,
        },
        "growth_rate": growth_rate,
        "delta_views": curr_total - prev_total,
    }
```

**Step 4: Run tests**

Run: `pytest djinsight/tests/test_mcp_tools_periods.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add djinsight/mcp/tools/periods.py djinsight/tests/test_mcp_tools_periods.py
git commit -m "feat: add period MCP tools (get_period_stats, compare_periods)"
```

---

### Task 5: Create trends tools module

**Files:**
- Create: `djinsight/mcp/tools/trends.py`
- Test: `djinsight/tests/test_mcp_tools_trends.py`

**Step 1: Write tests**

```python
"""Tests for trends MCP tools."""
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from djinsight.mcp.tools.trends import get_trending_pages
from djinsight.models import PageViewEvent, PageViewStatistics


class GetTrendingPagesTest(TestCase):
    def setUp(self):
        self.ct = ContentType.objects.get_for_model(PageViewStatistics)
        self.ct_str = f"{self.ct.app_label}.{self.ct.model}"
        now = timezone.now()

        # Object 1: growing (2 prev, 10 current)
        for i in range(2):
            PageViewEvent.objects.create(
                content_type=self.ct, object_id=1, url="/a/",
                session_key=f"prev-1-{i}", timestamp=now - timedelta(days=10),
            )
        for i in range(10):
            PageViewEvent.objects.create(
                content_type=self.ct, object_id=1, url="/a/",
                session_key=f"curr-1-{i}", timestamp=now - timedelta(hours=i),
            )

        # Object 2: declining (8 prev, 1 current)
        for i in range(8):
            PageViewEvent.objects.create(
                content_type=self.ct, object_id=2, url="/b/",
                session_key=f"prev-2-{i}", timestamp=now - timedelta(days=10),
            )
        PageViewEvent.objects.create(
            content_type=self.ct, object_id=2, url="/b/",
            session_key="curr-2-0", timestamp=now,
        )

    def test_trending_up(self):
        result = get_trending_pages(self.ct_str, period="week", direction="up", limit=5)
        self.assertGreater(len(result["results"]), 0)
        self.assertGreater(result["results"][0]["growth_rate"], 0)

    def test_trending_down(self):
        result = get_trending_pages(self.ct_str, period="week", direction="down", limit=5)
        self.assertGreater(len(result["results"]), 0)
        self.assertLess(result["results"][0]["growth_rate"], 0)

    def test_invalid_content_type(self):
        result = get_trending_pages("fake.model")
        self.assertIn("error", result)
```

**Step 2: Run tests to verify they fail**

Run: `pytest djinsight/tests/test_mcp_tools_trends.py -v`

**Step 3: Implement trends tool**

```python
"""Trends MCP tools: get_trending_pages."""
from datetime import timedelta
from typing import Any, Dict

from django.db.models import Count

from djinsight.mcp.utils import parse_content_type_str, parse_date_range
from djinsight.models import PageViewEvent


def get_trending_pages(
    content_type: str,
    period: str = "week",
    direction: str = "up",
    limit: int = 10,
) -> Dict[str, Any]:
    """Get pages with the biggest growth or decline in views.

    Args:
        content_type: Content type in format 'app_label.model'
        period: Time period ('today', 'week', 'month', 'year')
        direction: 'up' for growing, 'down' for declining
        limit: Number of results (default: 10)
    """
    ct = parse_content_type_str(content_type)
    if not ct:
        return {"error": f"Invalid content type: {content_type}"}

    try:
        current_start, current_end = parse_date_range(period)
    except ValueError as e:
        return {"error": str(e)}

    duration = current_end - current_start
    previous_end = current_start - timedelta(seconds=1)
    previous_start = previous_end - duration

    # Count views per object in both periods
    current_counts = dict(
        PageViewEvent.objects.filter(
            content_type=ct,
            timestamp__gte=current_start, timestamp__lte=current_end,
        ).values_list("object_id").annotate(count=Count("id")).values_list("object_id", "count")
    )

    previous_counts = dict(
        PageViewEvent.objects.filter(
            content_type=ct,
            timestamp__gte=previous_start, timestamp__lte=previous_end,
        ).values_list("object_id").annotate(count=Count("id")).values_list("object_id", "count")
    )

    # Compute growth for all objects present in either period
    all_objects = set(current_counts.keys()) | set(previous_counts.keys())
    trends = []
    for obj_id in all_objects:
        curr = current_counts.get(obj_id, 0)
        prev = previous_counts.get(obj_id, 0)
        if prev > 0:
            growth = round(((curr - prev) / prev) * 100, 1)
        elif curr > 0:
            growth = 100.0
        else:
            growth = 0.0
        trends.append({
            "object_id": obj_id,
            "current_views": curr,
            "previous_views": prev,
            "growth_rate": growth,
            "delta": curr - prev,
        })

    # Sort by growth rate
    reverse = direction == "up"
    trends.sort(key=lambda x: x["growth_rate"], reverse=reverse)
    trends = trends[:limit]

    # Fetch object names
    model_class = ct.model_class()
    obj_ids = [t["object_id"] for t in trends]
    names = {}
    try:
        for obj in model_class.objects.filter(pk__in=obj_ids):
            names[obj.pk] = str(obj)
    except Exception:
        pass

    for t in trends:
        t["object"] = names.get(t["object_id"])

    return {
        "content_type": content_type,
        "period": period,
        "direction": direction,
        "results": trends,
    }
```

**Step 4: Run tests**

Run: `pytest djinsight/tests/test_mcp_tools_trends.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add djinsight/mcp/tools/trends.py djinsight/tests/test_mcp_tools_trends.py
git commit -m "feat: add trending pages MCP tool"
```

---

### Task 6: Create referrers tools module

**Files:**
- Create: `djinsight/mcp/tools/referrers.py`
- Test: `djinsight/tests/test_mcp_tools_referrers.py`

**Step 1: Write tests**

```python
"""Tests for referrer MCP tools."""
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from djinsight.mcp.tools.referrers import get_referrer_stats, get_traffic_sources
from djinsight.models import PageViewEvent, PageViewStatistics


class GetReferrerStatsTest(TestCase):
    def setUp(self):
        self.ct = ContentType.objects.get_for_model(PageViewStatistics)
        self.ct_str = f"{self.ct.app_label}.{self.ct.model}"
        now = timezone.now()
        referrers = [
            "https://www.google.com/search?q=test",
            "https://www.google.com/search?q=other",
            "https://facebook.com/post/1",
            "https://blog.example.com/article",
            "",  # direct
        ]
        for i, ref in enumerate(referrers):
            PageViewEvent.objects.create(
                content_type=self.ct, object_id=1, url="/test/",
                session_key=f"s-{i}", referrer=ref, timestamp=now,
            )

    def test_returns_grouped_referrers(self):
        result = get_referrer_stats(self.ct_str, object_id=1)
        self.assertIn("referrers", result)
        self.assertGreater(len(result["referrers"]), 0)

    def test_content_type_level(self):
        result = get_referrer_stats(self.ct_str)
        self.assertIn("referrers", result)


class GetTrafficSourcesTest(TestCase):
    def setUp(self):
        self.ct = ContentType.objects.get_for_model(PageViewStatistics)
        self.ct_str = f"{self.ct.app_label}.{self.ct.model}"
        now = timezone.now()
        referrers = [
            "https://google.com/search", "https://facebook.com", "",
            "https://blog.example.com",
        ]
        for i, ref in enumerate(referrers):
            PageViewEvent.objects.create(
                content_type=self.ct, object_id=1, url="/test/",
                session_key=f"s-{i}", referrer=ref, timestamp=now,
            )

    def test_returns_source_categories(self):
        result = get_traffic_sources(self.ct_str)
        self.assertIn("sources", result)
        categories = {s["source"] for s in result["sources"]}
        self.assertTrue(categories)  # At least one category
```

**Step 2: Run tests to verify they fail**

Run: `pytest djinsight/tests/test_mcp_tools_referrers.py -v`

**Step 3: Implement referrer tools**

```python
"""Referrer MCP tools: get_referrer_stats, get_traffic_sources."""
from collections import Counter
from typing import Any, Dict, Optional

from django.db.models import Count

from djinsight.mcp.utils import (
    classify_referrer,
    extract_domain,
    parse_content_type_str,
    parse_date_range,
)
from djinsight.models import PageViewEvent


def get_referrer_stats(
    content_type: str,
    object_id: Optional[int] = None,
    period: str = "month",
    limit: int = 20,
) -> Dict[str, Any]:
    """Get top referrers grouped by domain.

    Args:
        content_type: Content type in format 'app_label.model'
        object_id: Optional object ID (if omitted, shows for entire content type)
        period: Time period ('today', 'week', 'month', 'year')
        limit: Number of results (default: 20)
    """
    ct = parse_content_type_str(content_type)
    if not ct:
        return {"error": f"Invalid content type: {content_type}"}

    try:
        start, end = parse_date_range(period)
    except ValueError as e:
        return {"error": str(e)}

    qs = PageViewEvent.objects.filter(
        content_type=ct, timestamp__gte=start, timestamp__lte=end,
    )
    if object_id is not None:
        qs = qs.filter(object_id=object_id)

    # Get all referrers and group by domain
    referrers = qs.values_list("referrer", flat=True)
    domain_counts = Counter()
    for ref in referrers:
        domain = extract_domain(ref)
        domain_counts[domain] += 1

    sorted_domains = domain_counts.most_common(limit)

    return {
        "content_type": content_type,
        "object_id": object_id,
        "period": period,
        "total_referrals": sum(domain_counts.values()),
        "referrers": [
            {"domain": domain, "views": count}
            for domain, count in sorted_domains
        ],
    }


def get_traffic_sources(
    content_type: str,
    object_id: Optional[int] = None,
    period: str = "month",
) -> Dict[str, Any]:
    """Get traffic sources aggregated by category (direct, search, social, referral).

    Args:
        content_type: Content type in format 'app_label.model'
        object_id: Optional object ID
        period: Time period ('today', 'week', 'month', 'year')
    """
    ct = parse_content_type_str(content_type)
    if not ct:
        return {"error": f"Invalid content type: {content_type}"}

    try:
        start, end = parse_date_range(period)
    except ValueError as e:
        return {"error": str(e)}

    qs = PageViewEvent.objects.filter(
        content_type=ct, timestamp__gte=start, timestamp__lte=end,
    )
    if object_id is not None:
        qs = qs.filter(object_id=object_id)

    referrers = qs.values_list("referrer", flat=True)
    source_counts = Counter()
    for ref in referrers:
        category = classify_referrer(ref)
        source_counts[category] += 1

    total = sum(source_counts.values())

    return {
        "content_type": content_type,
        "object_id": object_id,
        "period": period,
        "total_views": total,
        "sources": [
            {
                "source": source,
                "views": count,
                "percentage": round((count / total) * 100, 1) if total > 0 else 0,
            }
            for source, count in source_counts.most_common()
        ],
    }
```

**Step 4: Run tests**

Run: `pytest djinsight/tests/test_mcp_tools_referrers.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add djinsight/mcp/tools/referrers.py djinsight/tests/test_mcp_tools_referrers.py
git commit -m "feat: add referrer MCP tools (get_referrer_stats, get_traffic_sources)"
```

---

### Task 7: Create behavior tools module

**Files:**
- Create: `djinsight/mcp/tools/behavior.py`
- Test: `djinsight/tests/test_mcp_tools_behavior.py`

**Step 1: Write tests**

```python
"""Tests for behavior MCP tools."""
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from djinsight.mcp.tools.behavior import get_device_breakdown, get_hourly_pattern
from djinsight.models import PageViewEvent, PageViewStatistics


class GetDeviceBreakdownTest(TestCase):
    def setUp(self):
        self.ct = ContentType.objects.get_for_model(PageViewStatistics)
        self.ct_str = f"{self.ct.app_label}.{self.ct.model}"
        now = timezone.now()
        user_agents = [
            ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0", "desktop"),
            ("Mozilla/5.0 (iPhone; CPU iPhone OS 14_0) Mobile", "mobile"),
            ("Mozilla/5.0 (iPad; CPU OS 14_0) Safari", "tablet"),
            ("Googlebot/2.1", "bot"),
        ]
        for i, (ua, _) in enumerate(user_agents):
            PageViewEvent.objects.create(
                content_type=self.ct, object_id=1, url="/test/",
                session_key=f"s-{i}", user_agent=ua, timestamp=now,
            )

    def test_returns_device_categories(self):
        result = get_device_breakdown(self.ct_str)
        self.assertIn("devices", result)
        categories = {d["device"] for d in result["devices"]}
        self.assertIn("desktop", categories)
        self.assertIn("mobile", categories)


class GetHourlyPatternTest(TestCase):
    def setUp(self):
        self.ct = ContentType.objects.get_for_model(PageViewStatistics)
        self.ct_str = f"{self.ct.app_label}.{self.ct.model}"
        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        for hour in [9, 9, 10, 14, 14, 14]:
            PageViewEvent.objects.create(
                content_type=self.ct, object_id=1, url="/test/",
                session_key=f"s-{hour}-{timezone.now().microsecond}",
                timestamp=now.replace(hour=hour),
            )

    def test_returns_24_hours(self):
        result = get_hourly_pattern(self.ct_str, period="today")
        self.assertIn("hours", result)
        self.assertEqual(len(result["hours"]), 24)

    def test_peak_hour(self):
        result = get_hourly_pattern(self.ct_str, period="today")
        self.assertIn("peak_hour", result)
```

**Step 2: Run tests to verify they fail**

Run: `pytest djinsight/tests/test_mcp_tools_behavior.py -v`

**Step 3: Implement behavior tools**

```python
"""Behavior MCP tools: get_device_breakdown, get_hourly_pattern."""
from collections import Counter
from typing import Any, Dict, Optional

from djinsight.mcp.utils import parse_content_type_str, parse_date_range, parse_user_agent_category
from djinsight.models import PageViewEvent


def get_device_breakdown(
    content_type: str,
    object_id: Optional[int] = None,
    period: str = "month",
) -> Dict[str, Any]:
    """Get device type breakdown (mobile, desktop, tablet, bot).

    Args:
        content_type: Content type in format 'app_label.model'
        object_id: Optional object ID
        period: Time period ('today', 'week', 'month', 'year')
    """
    ct = parse_content_type_str(content_type)
    if not ct:
        return {"error": f"Invalid content type: {content_type}"}

    try:
        start, end = parse_date_range(period)
    except ValueError as e:
        return {"error": str(e)}

    qs = PageViewEvent.objects.filter(
        content_type=ct, timestamp__gte=start, timestamp__lte=end,
    )
    if object_id is not None:
        qs = qs.filter(object_id=object_id)

    user_agents = qs.values_list("user_agent", flat=True)
    device_counts = Counter()
    for ua in user_agents:
        category = parse_user_agent_category(ua)
        device_counts[category] += 1

    total = sum(device_counts.values())

    return {
        "content_type": content_type,
        "object_id": object_id,
        "period": period,
        "total_views": total,
        "devices": [
            {
                "device": device,
                "views": count,
                "percentage": round((count / total) * 100, 1) if total > 0 else 0,
            }
            for device, count in device_counts.most_common()
        ],
    }


def get_hourly_pattern(
    content_type: str,
    object_id: Optional[int] = None,
    period: str = "week",
) -> Dict[str, Any]:
    """Get hourly traffic distribution pattern.

    Args:
        content_type: Content type in format 'app_label.model'
        object_id: Optional object ID
        period: Time period to analyze
    """
    ct = parse_content_type_str(content_type)
    if not ct:
        return {"error": f"Invalid content type: {content_type}"}

    try:
        start, end = parse_date_range(period)
    except ValueError as e:
        return {"error": str(e)}

    qs = PageViewEvent.objects.filter(
        content_type=ct, timestamp__gte=start, timestamp__lte=end,
    )
    if object_id is not None:
        qs = qs.filter(object_id=object_id)

    # Count by hour
    hourly_counts = Counter()
    for ts in qs.values_list("timestamp", flat=True):
        hourly_counts[ts.hour] += 1

    hours = []
    for h in range(24):
        hours.append({
            "hour": h,
            "label": f"{h:02d}:00",
            "views": hourly_counts.get(h, 0),
        })

    total = sum(hourly_counts.values())
    peak_hour = max(range(24), key=lambda h: hourly_counts.get(h, 0)) if total > 0 else None

    return {
        "content_type": content_type,
        "object_id": object_id,
        "period": period,
        "total_views": total,
        "peak_hour": f"{peak_hour:02d}:00" if peak_hour is not None else None,
        "hours": hours,
    }
```

**Step 4: Run tests**

Run: `pytest djinsight/tests/test_mcp_tools_behavior.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add djinsight/mcp/tools/behavior.py djinsight/tests/test_mcp_tools_behavior.py
git commit -m "feat: add behavior MCP tools (get_device_breakdown, get_hourly_pattern)"
```

---

### Task 8: Create cross-model tools module

**Files:**
- Create: `djinsight/mcp/tools/cross_model.py`
- Test: `djinsight/tests/test_mcp_tools_cross_model.py`

**Step 1: Write tests**

```python
"""Tests for cross-model MCP tools."""
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from djinsight.mcp.tools.cross_model import compare_content_types, get_site_overview
from djinsight.models import PageViewEvent, PageViewStatistics, PageViewSummary


class GetSiteOverviewTest(TestCase):
    def setUp(self):
        ct1 = ContentType.objects.get_for_model(PageViewStatistics)
        ct2 = ContentType.objects.get_for_model(PageViewSummary)
        now = timezone.now()
        PageViewStatistics.objects.create(
            content_type=ct1, object_id=1, total_views=100, unique_views=50,
        )
        PageViewStatistics.objects.create(
            content_type=ct2, object_id=1, total_views=200, unique_views=80,
        )

    def test_returns_site_totals(self):
        result = get_site_overview()
        self.assertIn("total_views", result)
        self.assertEqual(result["total_views"], 300)
        self.assertEqual(result["total_unique_views"], 130)
        self.assertEqual(result["tracked_objects"], 2)

    def test_returns_content_type_breakdown(self):
        result = get_site_overview()
        self.assertIn("by_content_type", result)
        self.assertEqual(len(result["by_content_type"]), 2)


class CompareContentTypesTest(TestCase):
    def setUp(self):
        self.ct1 = ContentType.objects.get_for_model(PageViewStatistics)
        self.ct2 = ContentType.objects.get_for_model(PageViewSummary)
        now = timezone.now()
        for i in range(10):
            PageViewEvent.objects.create(
                content_type=self.ct1, object_id=1, url="/a/",
                session_key=f"s1-{i}", timestamp=now,
            )
        for i in range(5):
            PageViewEvent.objects.create(
                content_type=self.ct2, object_id=1, url="/b/",
                session_key=f"s2-{i}", timestamp=now,
            )

    def test_compare_returns_both(self):
        ct1_str = f"{self.ct1.app_label}.{self.ct1.model}"
        ct2_str = f"{self.ct2.app_label}.{self.ct2.model}"
        result = compare_content_types([ct1_str, ct2_str])
        self.assertIn("content_types", result)
        self.assertEqual(len(result["content_types"]), 2)

    def test_invalid_content_type(self):
        result = compare_content_types(["fake.model"])
        self.assertEqual(len(result["content_types"]), 0)
```

**Step 2: Run tests to verify they fail**

Run: `pytest djinsight/tests/test_mcp_tools_cross_model.py -v`

**Step 3: Implement cross-model tools**

```python
"""Cross-model MCP tools: get_site_overview, compare_content_types."""
from typing import Any, Dict, List

from django.db.models import Sum

from djinsight.mcp.utils import parse_content_type_str, parse_date_range
from djinsight.models import PageViewEvent, PageViewStatistics


def get_site_overview() -> Dict[str, Any]:
    """Get site-wide overview of all tracked content across all content types."""
    all_stats = PageViewStatistics.objects.all()

    totals = all_stats.aggregate(
        total_views=Sum("total_views"),
        total_unique=Sum("unique_views"),
    )

    # Breakdown by content type
    by_ct = (
        all_stats.values("content_type__app_label", "content_type__model")
        .annotate(
            views=Sum("total_views"),
            unique=Sum("unique_views"),
        )
        .order_by("-views")
    )

    return {
        "total_views": totals["total_views"] or 0,
        "total_unique_views": totals["total_unique"] or 0,
        "tracked_objects": all_stats.count(),
        "by_content_type": [
            {
                "content_type": f"{ct['content_type__app_label']}.{ct['content_type__model']}",
                "total_views": ct["views"] or 0,
                "unique_views": ct["unique"] or 0,
            }
            for ct in by_ct
        ],
    }


def compare_content_types(
    content_types: List[str],
    period: str = "month",
) -> Dict[str, Any]:
    """Compare traffic between different content types.

    Args:
        content_types: List of content type strings in format 'app_label.model'
        period: Time period ('today', 'week', 'month', 'year')
    """
    try:
        start, end = parse_date_range(period)
    except ValueError as e:
        return {"error": str(e)}

    results = []
    for ct_str in content_types:
        ct = parse_content_type_str(ct_str)
        if not ct:
            continue

        qs = PageViewEvent.objects.filter(
            content_type=ct, timestamp__gte=start, timestamp__lte=end,
        )
        total = qs.count()
        unique = qs.values("session_key").distinct().count()

        results.append({
            "content_type": ct_str,
            "total_views": total,
            "unique_views": unique,
        })

    results.sort(key=lambda x: x["total_views"], reverse=True)

    return {
        "period": period,
        "content_types": results,
    }
```

**Step 4: Run tests**

Run: `pytest djinsight/tests/test_mcp_tools_cross_model.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add djinsight/mcp/tools/cross_model.py djinsight/tests/test_mcp_tools_cross_model.py
git commit -m "feat: add cross-model MCP tools (get_site_overview, compare_content_types)"
```

---

### Task 9: Create search tools module

**Files:**
- Create: `djinsight/mcp/tools/search.py`
- Test: `djinsight/tests/test_mcp_tools_search.py`

**Step 1: Write tests**

```python
"""Tests for search MCP tools."""
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from djinsight.mcp.tools.search import search_pages
from djinsight.models import ContentTypeRegistry, PageViewStatistics


class SearchPagesTest(TestCase):
    def setUp(self):
        self.ct = ContentType.objects.get_for_model(PageViewStatistics)
        self.ct_str = f"{self.ct.app_label}.{self.ct.model}"
        ContentTypeRegistry.register(PageViewStatistics)
        PageViewStatistics.objects.create(
            content_type=self.ct, object_id=1, total_views=50, unique_views=20,
        )

    def test_search_returns_results(self):
        result = search_pages("pageview")
        self.assertIn("results", result)

    def test_search_with_content_type_filter(self):
        result = search_pages("pageview", content_type=self.ct_str)
        self.assertIn("results", result)

    def test_empty_query(self):
        result = search_pages("")
        self.assertIn("error", result)
```

**Step 2: Run tests to verify they fail**

Run: `pytest djinsight/tests/test_mcp_tools_search.py -v`

**Step 3: Implement search tool**

```python
"""Search MCP tools: search_pages."""
from typing import Any, Dict, Optional

from django.contrib.contenttypes.models import ContentType

from djinsight.mcp.utils import parse_content_type_str
from djinsight.models import ContentTypeRegistry, PageViewStatistics


def search_pages(
    query: str,
    content_type: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """Search tracked objects by name/title and return with their stats.

    Args:
        query: Search query to match against object string representation
        content_type: Optional content type filter in format 'app_label.model'
        limit: Max results (default: 20)
    """
    if not query or not query.strip():
        return {"error": "Query is required"}

    query = query.strip().lower()

    # Determine which content types to search
    if content_type:
        ct = parse_content_type_str(content_type)
        if not ct:
            return {"error": f"Invalid content type: {content_type}"}
        content_types = [ct]
    else:
        registries = ContentTypeRegistry.objects.filter(enabled=True).select_related("content_type")
        content_types = [r.content_type for r in registries]

    results = []
    for ct in content_types:
        model_class = ct.model_class()
        if not model_class:
            continue

        # Try common search fields
        search_fields = []
        for field_name in ("title", "name", "headline", "subject"):
            if hasattr(model_class, field_name):
                search_fields.append(field_name)

        if search_fields:
            from django.db.models import Q
            q_filter = Q()
            for field in search_fields:
                q_filter |= Q(**{f"{field}__icontains": query})
            objects = model_class.objects.filter(q_filter)[:limit]
        else:
            # Fallback: get all objects and filter by str()
            objects = model_class.objects.all()[:200]
            objects = [o for o in objects if query in str(o).lower()][:limit]

        for obj in objects:
            stats = PageViewStatistics.objects.filter(
                content_type=ct, object_id=obj.pk,
            ).first()

            results.append({
                "content_type": f"{ct.app_label}.{ct.model}",
                "object_id": obj.pk,
                "object": str(obj),
                "total_views": stats.total_views if stats else 0,
                "unique_views": stats.unique_views if stats else 0,
            })

    results.sort(key=lambda x: x["total_views"], reverse=True)

    return {
        "query": query,
        "total_results": len(results),
        "results": results[:limit],
    }
```

**Step 4: Run tests**

Run: `pytest djinsight/tests/test_mcp_tools_search.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add djinsight/mcp/tools/search.py djinsight/tests/test_mcp_tools_search.py
git commit -m "feat: add search_pages MCP tool"
```

---

### Task 10: Create FastMCP server and entry point

**Files:**
- Rewrite: `djinsight/mcp/server.py`
- Create: `djinsight/mcp/__main__.py`
- Modify: `djinsight/mcp/__init__.py`
- Test: `djinsight/tests/test_mcp_server.py`

**Step 1: Write tests for server tool registration**

```python
"""Tests for MCP server tool registration."""
from unittest.mock import patch

from django.test import TestCase


class MCPServerRegistrationTest(TestCase):
    def test_server_has_all_tools(self):
        """Verify all 13 tools are registered."""
        from djinsight.mcp.server import mcp

        # FastMCP stores tools internally
        tools = mcp._tool_manager.list_tools()
        tool_names = {t.name for t in tools}

        expected = {
            "get_page_stats", "get_top_pages", "list_tracked_models",
            "get_period_stats", "compare_periods",
            "get_trending_pages",
            "get_referrer_stats", "get_traffic_sources",
            "get_device_breakdown", "get_hourly_pattern",
            "get_site_overview", "compare_content_types",
            "search_pages",
        }
        self.assertEqual(tool_names, expected)
```

**Step 2: Run test to verify it fails**

Run: `pytest djinsight/tests/test_mcp_server.py -v`

**Step 3: Implement server.py**

Replace the entire `djinsight/mcp/server.py` with:

```python
"""Native MCP server for djinsight using FastMCP."""
import json
from typing import List, Optional

from mcp.server.fastmcp import FastMCP

from djinsight.mcp.tools.basic import (
    get_page_stats as _get_page_stats,
    get_top_pages as _get_top_pages,
    list_tracked_models as _list_tracked_models,
)
from djinsight.mcp.tools.periods import (
    compare_periods as _compare_periods,
    get_period_stats as _get_period_stats,
)
from djinsight.mcp.tools.trends import get_trending_pages as _get_trending_pages
from djinsight.mcp.tools.referrers import (
    get_referrer_stats as _get_referrer_stats,
    get_traffic_sources as _get_traffic_sources,
)
from djinsight.mcp.tools.behavior import (
    get_device_breakdown as _get_device_breakdown,
    get_hourly_pattern as _get_hourly_pattern,
)
from djinsight.mcp.tools.cross_model import (
    compare_content_types as _compare_content_types,
    get_site_overview as _get_site_overview,
)
from djinsight.mcp.tools.search import search_pages as _search_pages

mcp = FastMCP(
    "djinsight",
    json_response=True,
)


# --- Basic tools ---

@mcp.tool()
def get_page_stats(content_type: str, object_id: int) -> str:
    """Get page view statistics for a specific object.

    Args:
        content_type: Content type in format 'app_label.model' (e.g., 'blog.post')
        object_id: The object's primary key
    """
    return json.dumps(_get_page_stats(content_type, object_id))


@mcp.tool()
def get_top_pages(content_type: str, limit: int = 10, metric: str = "total_views") -> str:
    """Get top performing pages by views.

    Args:
        content_type: Content type in format 'app_label.model'
        limit: Number of results (default: 10)
        metric: Sort by 'total_views' or 'unique_views'
    """
    return json.dumps(_get_top_pages(content_type, limit, metric))


@mcp.tool()
def list_tracked_models() -> str:
    """List all content types that are being tracked."""
    return json.dumps(_list_tracked_models())


# --- Period tools ---

@mcp.tool()
def get_period_stats(
    content_type: str,
    object_id: int,
    period: str = "week",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> str:
    """Get view statistics for a specific time period with daily breakdown.

    Args:
        content_type: Content type in format 'app_label.model'
        object_id: The object's primary key
        period: 'today', 'week', 'month', 'year', or 'custom'
        start_date: Start date for custom period (YYYY-MM-DD)
        end_date: End date for custom period (YYYY-MM-DD)
    """
    return json.dumps(_get_period_stats(content_type, object_id, period, start_date, end_date))


@mcp.tool()
def compare_periods(content_type: str, object_id: int, period: str = "week") -> str:
    """Compare current period with previous period. Shows growth rate and view delta.

    Args:
        content_type: Content type in format 'app_label.model'
        object_id: The object's primary key
        period: 'today', 'week', 'month', or 'year'
    """
    return json.dumps(_compare_periods(content_type, object_id, period))


# --- Trends ---

@mcp.tool()
def get_trending_pages(
    content_type: str,
    period: str = "week",
    direction: str = "up",
    limit: int = 10,
) -> str:
    """Get pages with biggest growth or decline in views compared to previous period.

    Args:
        content_type: Content type in format 'app_label.model'
        period: Time period ('today', 'week', 'month', 'year')
        direction: 'up' for growing pages, 'down' for declining
        limit: Number of results (default: 10)
    """
    return json.dumps(_get_trending_pages(content_type, period, direction, limit))


# --- Referrers ---

@mcp.tool()
def get_referrer_stats(
    content_type: str,
    object_id: Optional[int] = None,
    period: str = "month",
    limit: int = 20,
) -> str:
    """Get top referrers grouped by domain.

    Args:
        content_type: Content type in format 'app_label.model'
        object_id: Optional - filter to specific object
        period: Time period ('today', 'week', 'month', 'year')
        limit: Number of referrer domains to return
    """
    return json.dumps(_get_referrer_stats(content_type, object_id, period, limit))


@mcp.tool()
def get_traffic_sources(
    content_type: str,
    object_id: Optional[int] = None,
    period: str = "month",
) -> str:
    """Get traffic sources by category: direct, search, social, referral.

    Args:
        content_type: Content type in format 'app_label.model'
        object_id: Optional - filter to specific object
        period: Time period ('today', 'week', 'month', 'year')
    """
    return json.dumps(_get_traffic_sources(content_type, object_id, period))


# --- Behavior ---

@mcp.tool()
def get_device_breakdown(
    content_type: str,
    object_id: Optional[int] = None,
    period: str = "month",
) -> str:
    """Get device type breakdown: mobile, desktop, tablet, bot.

    Args:
        content_type: Content type in format 'app_label.model'
        object_id: Optional - filter to specific object
        period: Time period ('today', 'week', 'month', 'year')
    """
    return json.dumps(_get_device_breakdown(content_type, object_id, period))


@mcp.tool()
def get_hourly_pattern(
    content_type: str,
    object_id: Optional[int] = None,
    period: str = "week",
) -> str:
    """Get hourly traffic distribution to identify peak hours.

    Args:
        content_type: Content type in format 'app_label.model'
        object_id: Optional - filter to specific object
        period: Time period to analyze
    """
    return json.dumps(_get_hourly_pattern(content_type, object_id, period))


# --- Cross-model ---

@mcp.tool()
def get_site_overview() -> str:
    """Get site-wide overview: total views, unique views, breakdown by content type."""
    return json.dumps(_get_site_overview())


@mcp.tool()
def compare_content_types(
    content_types: List[str],
    period: str = "month",
) -> str:
    """Compare traffic between different content types.

    Args:
        content_types: List of content type strings (e.g., ['blog.post', 'shop.product'])
        period: Time period ('today', 'week', 'month', 'year')
    """
    return json.dumps(_compare_content_types(content_types, period))


# --- Search ---

@mcp.tool()
def search_pages(
    query: str,
    content_type: Optional[str] = None,
    limit: int = 20,
) -> str:
    """Search tracked objects by name/title and return with their view stats.

    Args:
        query: Search query text
        content_type: Optional content type filter
        limit: Max results (default: 20)
    """
    return json.dumps(_search_pages(query, content_type, limit))
```

**Step 4: Create `__main__.py`**

```python
"""Entry point for running djinsight MCP server: python -m djinsight.mcp"""
import os
import sys


def main():
    # Django setup
    settings_module = os.environ.get("DJANGO_SETTINGS_MODULE")
    if not settings_module:
        print(
            "Error: DJANGO_SETTINGS_MODULE environment variable is required.\n"
            "Example: DJANGO_SETTINGS_MODULE=myproject.settings python -m djinsight.mcp",
            file=sys.stderr,
        )
        sys.exit(1)

    import django
    django.setup()

    from djinsight.mcp.server import mcp
    mcp.run()


if __name__ == "__main__":
    main()
```

**Step 5: Update `__init__.py`**

```python
```

(Empty file — the old MCPServer class import is no longer needed)

**Step 6: Run tests**

Run: `pytest djinsight/tests/test_mcp_server.py -v`
Expected: PASS (may need to adjust based on actual FastMCP internal API — check `_tool_manager` attribute name)

**Step 7: Commit**

```bash
git add djinsight/mcp/server.py djinsight/mcp/__main__.py djinsight/mcp/__init__.py djinsight/tests/test_mcp_server.py
git commit -m "feat: replace HTTP MCP endpoint with native FastMCP server (13 tools)"
```

---

### Task 11: Clean up old MCP code

**Files:**
- Modify: `djinsight/urls.py` — remove MCP endpoint
- Delete: `mcp-package/` directory (Node.js wrapper)

**Step 1: Update urls.py**

Remove the MCP import and URL pattern. New content:

```python
from django.urls import path

from djinsight import views

app_name = "djinsight"

urlpatterns = [
    path("record-view/", views.record_page_view, name="record_page_view"),
    path("page-stats/", views.get_page_stats, name="get_page_stats"),
]
```

**Step 2: Verify existing tests still pass**

Run: `pytest -v`
Expected: All existing tests pass (test_views.py may reference mcp_endpoint — check and fix if needed)

**Step 3: Commit cleanup**

```bash
git rm -r mcp-package/
git add djinsight/urls.py
git commit -m "refactor: remove old HTTP MCP endpoint and Node.js wrapper"
```

---

### Task 12: Run full test suite and fix issues

**Step 1: Run all tests**

Run: `pytest --tb=long -v`

Fix any failures. Common issues to watch for:
- `test_views.py` may reference `mcp_endpoint` URL — remove those tests
- Import errors if `mcp` package not installed — ensure tests skip gracefully or install it

**Step 2: Run linting**

Run: `black djinsight/ && isort djinsight/ && flake8 djinsight/`

**Step 3: Final commit**

```bash
git add -A
git commit -m "fix: resolve test and lint issues after MCP refactor"
```

---

### Task 13: Update documentation

**Files:**
- Modify: `CLAUDE.md` — update MCP section
- Modify: `README.md` — update MCP setup instructions (if exists)

**Step 1: Update CLAUDE.md MCP section**

Update the architecture section to reflect:
- 13 MCP tools instead of 4
- Native Python MCP server (no Node.js)
- Entry point: `python -m djinsight.mcp`
- Tools organized in `djinsight/mcp/tools/` modules

**Step 2: Commit**

```bash
git add CLAUDE.md README.md
git commit -m "docs: update MCP documentation for native Python server"
```
