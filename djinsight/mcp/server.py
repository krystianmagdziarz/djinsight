"""Native MCP server for djinsight using FastMCP."""

import json
from typing import List, Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("djinsight", json_response=True)

# Import tool functions with _ prefix to avoid name collision
from djinsight.mcp.tools.basic import get_page_stats as _get_page_stats  # noqa: E402
from djinsight.mcp.tools.basic import get_top_pages as _get_top_pages
from djinsight.mcp.tools.basic import list_tracked_models as _list_tracked_models
from djinsight.mcp.tools.behavior import (  # noqa: E402
    get_device_breakdown as _get_device_breakdown,
)
from djinsight.mcp.tools.behavior import get_hourly_pattern as _get_hourly_pattern
from djinsight.mcp.tools.cross_model import (
    compare_content_types as _compare_content_types,
)
from djinsight.mcp.tools.cross_model import (  # noqa: E402
    get_site_overview as _get_site_overview,
)
from djinsight.mcp.tools.periods import compare_periods as _compare_periods
from djinsight.mcp.tools.periods import (  # noqa: E402
    get_period_stats as _get_period_stats,
)
from djinsight.mcp.tools.referrers import (  # noqa: E402
    get_referrer_stats as _get_referrer_stats,
)
from djinsight.mcp.tools.referrers import get_traffic_sources as _get_traffic_sources
from djinsight.mcp.tools.search import search_pages as _search_pages  # noqa: E402
from djinsight.mcp.tools.trends import (  # noqa: E402
    get_trending_pages as _get_trending_pages,
)


@mcp.tool()
def get_page_stats(content_type: str, object_id: int) -> str:
    """Get page view statistics for a specific object. Provide content_type as 'app_label.model' (e.g. 'blog.post') and the object's primary key."""
    return json.dumps(_get_page_stats(content_type, object_id))


@mcp.tool()
def get_top_pages(
    content_type: str, limit: int = 10, metric: str = "total_views"
) -> str:
    """Get top pages sorted by a metric. Returns pages ordered by total_views or unique_views for the given content type."""
    return json.dumps(_get_top_pages(content_type, limit=limit, metric=metric))


@mcp.tool()
def list_tracked_models() -> str:
    """List all content types currently being tracked by djinsight."""
    return json.dumps(_list_tracked_models())


@mcp.tool()
def get_period_stats(
    content_type: str,
    object_id: int,
    period: str = "week",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> str:
    """Get view statistics for a specific time period. Supports 'today', 'week', 'month', 'year' or custom date ranges."""
    return json.dumps(
        _get_period_stats(
            content_type,
            object_id,
            period=period,
            start_date=start_date,
            end_date=end_date,
        )
    )


@mcp.tool()
def compare_periods(content_type: str, object_id: int, period: str = "week") -> str:
    """Compare current vs previous period view statistics, showing growth trends."""
    return json.dumps(_compare_periods(content_type, object_id, period=period))


@mcp.tool()
def get_trending_pages(
    content_type: str, period: str = "week", direction: str = "up", limit: int = 10
) -> str:
    """Get trending pages with the biggest view changes. Use direction='up' for rising or 'down' for declining."""
    return json.dumps(
        _get_trending_pages(
            content_type, period=period, direction=direction, limit=limit
        )
    )


@mcp.tool()
def get_referrer_stats(
    content_type: str,
    object_id: Optional[int] = None,
    period: str = "month",
    limit: int = 20,
) -> str:
    """Get referrer statistics showing where traffic comes from. Optionally filter by specific object."""
    return json.dumps(
        _get_referrer_stats(
            content_type, object_id=object_id, period=period, limit=limit
        )
    )


@mcp.tool()
def get_traffic_sources(
    content_type: str, object_id: Optional[int] = None, period: str = "month"
) -> str:
    """Get traffic sources grouped by category (search, social, direct, referral)."""
    return json.dumps(
        _get_traffic_sources(content_type, object_id=object_id, period=period)
    )


@mcp.tool()
def get_device_breakdown(
    content_type: str, object_id: Optional[int] = None, period: str = "month"
) -> str:
    """Get device type breakdown (desktop, mobile, tablet) for page views."""
    return json.dumps(
        _get_device_breakdown(content_type, object_id=object_id, period=period)
    )


@mcp.tool()
def get_hourly_pattern(
    content_type: str, object_id: Optional[int] = None, period: str = "week"
) -> str:
    """Get hourly traffic distribution showing when users visit most."""
    return json.dumps(
        _get_hourly_pattern(content_type, object_id=object_id, period=period)
    )


@mcp.tool()
def get_site_overview() -> str:
    """Get a high-level overview of all tracked content across the site."""
    return json.dumps(_get_site_overview())


@mcp.tool()
def compare_content_types(content_types: List[str], period: str = "month") -> str:
    """Compare statistics across multiple content types side by side."""
    return json.dumps(_compare_content_types(content_types, period=period))


@mcp.tool()
def search_pages(
    query: str, content_type: Optional[str] = None, limit: int = 20
) -> str:
    """Search tracked pages by name or title and return matching results with their view statistics."""
    return json.dumps(_search_pages(query, content_type=content_type, limit=limit))
