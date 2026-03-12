"""Period-based analytics tools for the djinsight MCP server."""

from typing import Dict, Optional

from django.db.models import Count
from django.db.models.functions import TruncDate

from djinsight.mcp.utils import parse_content_type_str, parse_date_range
from djinsight.models import PageViewEvent


def get_period_stats(
    content_type: str,
    object_id: int,
    period: str = "week",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict:
    """Get view stats for a time period.

    Args:
        content_type: 'app_label.model' string.
        object_id: The object's primary key.
        period: One of 'today', 'week', 'month', 'year', 'custom'.
        start_date: Required for 'custom' period, format 'YYYY-MM-DD'.
        end_date: Required for 'custom' period, format 'YYYY-MM-DD'.

    Returns:
        Dict with content_type, object_id, period, start_date, end_date,
        total_views, unique_views, and daily_breakdown.
    """
    ct = parse_content_type_str(content_type)
    if ct is None:
        return {"error": f"Invalid content type: {content_type}"}

    try:
        start_dt, end_dt = parse_date_range(period, start_date, end_date)
    except ValueError as e:
        return {"error": str(e)}

    events = PageViewEvent.objects.filter(
        content_type=ct,
        object_id=object_id,
        timestamp__gte=start_dt,
        timestamp__lte=end_dt,
    )

    total_views = events.count()
    unique_views = events.values("session_key").distinct().count()

    daily = (
        events.annotate(day=TruncDate("timestamp"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )

    daily_breakdown = [
        {"date": str(entry["day"]), "views": entry["count"]} for entry in daily
    ]

    return {
        "content_type": content_type,
        "object_id": object_id,
        "period": period,
        "start_date": str(start_dt.date()),
        "end_date": str(end_dt.date()),
        "total_views": total_views,
        "unique_views": unique_views,
        "daily_breakdown": daily_breakdown,
    }


def compare_periods(
    content_type: str,
    object_id: int,
    period: str = "week",
) -> Dict:
    """Compare current vs previous period view stats.

    Args:
        content_type: 'app_label.model' string.
        object_id: The object's primary key.
        period: One of 'today', 'week', 'month', 'year'.

    Returns:
        Dict with content_type, object_id, period, current_period,
        previous_period, growth_rate, and delta_views.
    """
    ct = parse_content_type_str(content_type)
    if ct is None:
        return {"error": f"Invalid content type: {content_type}"}

    try:
        current_start, current_end = parse_date_range(period)
    except ValueError as e:
        return {"error": str(e)}

    duration = current_end - current_start

    previous_end = current_start
    previous_start = previous_end - duration

    current_events = PageViewEvent.objects.filter(
        content_type=ct,
        object_id=object_id,
        timestamp__gte=current_start,
        timestamp__lte=current_end,
    )
    current_views = current_events.count()

    previous_events = PageViewEvent.objects.filter(
        content_type=ct,
        object_id=object_id,
        timestamp__gte=previous_start,
        timestamp__lt=previous_end,
    )
    previous_views = previous_events.count()

    delta = current_views - previous_views
    if previous_views > 0:
        growth_rate = round((delta / previous_views) * 100, 2)
    else:
        growth_rate = 100.0 if current_views > 0 else 0.0

    return {
        "content_type": content_type,
        "object_id": object_id,
        "period": period,
        "current_period": {
            "start_date": str(current_start.date()),
            "end_date": str(current_end.date()),
            "total_views": current_views,
        },
        "previous_period": {
            "start_date": str(previous_start.date()),
            "end_date": str(previous_end.date()),
            "total_views": previous_views,
        },
        "growth_rate": growth_rate,
        "delta_views": delta,
    }
