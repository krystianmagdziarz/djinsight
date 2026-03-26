"""Cross-model MCP tools for djinsight."""

import logging
from typing import Dict, List

from django.db.models import Count, Sum

from djinsight.mcp.utils import parse_content_type_str, parse_date_range
from djinsight.models import PageViewEvent, PageViewStatistics

logger = logging.getLogger(__name__)


def get_site_overview() -> Dict:
    """Get site-wide overview of all tracked content.

    Aggregates all PageViewStatistics to provide a high-level summary
    including totals and a breakdown by content type.

    Returns:
        Dict with total_views, total_unique_views, tracked_objects,
        and by_content_type list.
    """
    aggregates = PageViewStatistics.objects.aggregate(
        total_views=Sum("total_views"),
        total_unique_views=Sum("unique_views"),
    )

    total_views = aggregates["total_views"] or 0
    total_unique_views = aggregates["total_unique_views"] or 0
    tracked_objects = PageViewStatistics.objects.count()

    by_content_type_qs = (
        PageViewStatistics.objects.values(
            "content_type__app_label", "content_type__model"
        )
        .annotate(
            total_views=Sum("total_views"),
            unique_views=Sum("unique_views"),
            object_count=Count("id"),
        )
        .order_by("-total_views")
    )

    by_content_type = [
        {
            "content_type": f"{row['content_type__app_label']}.{row['content_type__model']}",
            "total_views": row["total_views"] or 0,
            "unique_views": row["unique_views"] or 0,
            "object_count": row["object_count"],
        }
        for row in by_content_type_qs
    ]

    return {
        "total_views": total_views,
        "total_unique_views": total_unique_views,
        "tracked_objects": tracked_objects,
        "by_content_type": by_content_type,
    }


def compare_content_types(content_types: List[str], period: str = "month") -> Dict:
    """Compare traffic between content types for a given period.

    Args:
        content_types: List of content type strings in 'app_label.model' format.
        period: One of 'today', 'week', 'month', 'year'.

    Returns:
        Dict with period and content_types list sorted by total_views desc.
        Each entry contains content_type, total_views, unique_views.
        Invalid content types are skipped.
    """
    try:
        start, end = parse_date_range(period)
    except ValueError as e:
        return {"error": str(e)}

    results = []
    for ct_str in content_types:
        ct = parse_content_type_str(ct_str)
        if ct is None:
            continue

        events = PageViewEvent.objects.filter(
            content_type=ct,
            timestamp__gte=start,
            timestamp__lte=end,
        )

        total_views = events.count()
        unique_views = events.values("session_key").distinct().count()

        results.append(
            {
                "content_type": ct_str,
                "total_views": total_views,
                "unique_views": unique_views,
            }
        )

    results.sort(key=lambda x: x["total_views"], reverse=True)

    return {
        "period": period,
        "content_types": results,
    }
