"""Behavior analysis MCP tools for djinsight."""

import logging
from collections import Counter
from typing import Dict

from django.db.models import Count
from django.db.models.functions import ExtractHour

from djinsight.mcp.utils import (
    parse_content_type_str,
    parse_date_range,
    parse_user_agent_category,
)
from djinsight.models import PageViewEvent

logger = logging.getLogger(__name__)


def get_device_breakdown(
    content_type: str, object_id: int = None, period: str = "month"
) -> Dict:
    """Get device type breakdown for page views.

    Args:
        content_type: Content type string in 'app_label.model' format.
        object_id: Optional object ID to filter by specific object.
        period: Time period - 'today', 'week', 'month', 'year'.

    Returns:
        Dict with content_type, object_id, period, total_views, and devices list.
        Each device entry has device, views, percentage.
    """
    ct = parse_content_type_str(content_type)
    if not ct:
        return {"error": f"Invalid content type: {content_type}"}

    try:
        start, end = parse_date_range(period)
    except ValueError as e:
        return {"error": str(e)}

    filters = {
        "content_type": ct,
        "timestamp__gte": start,
        "timestamp__lte": end,
    }
    if object_id is not None:
        filters["object_id"] = object_id

    events = PageViewEvent.objects.filter(**filters)

    counter = Counter()
    for ua in events.values_list("user_agent", flat=True).iterator():
        category = parse_user_agent_category(ua)
        counter[category] += 1

    total_views = sum(counter.values())

    devices = [
        {
            "device": device,
            "views": views,
            "percentage": round(views / total_views * 100, 1) if total_views else 0,
        }
        for device, views in counter.most_common()
    ]

    return {
        "content_type": content_type,
        "object_id": object_id,
        "period": period,
        "total_views": total_views,
        "devices": devices,
    }


def get_hourly_pattern(
    content_type: str, object_id: int = None, period: str = "week"
) -> Dict:
    """Get hourly traffic distribution for page views.

    Args:
        content_type: Content type string in 'app_label.model' format.
        object_id: Optional object ID to filter by specific object.
        period: Time period - 'today', 'week', 'month', 'year'.

    Returns:
        Dict with content_type, object_id, period, total_views, peak_hour,
        and hours list (all 24 hours). Each hour entry has hour, label, views.
    """
    ct = parse_content_type_str(content_type)
    if not ct:
        return {"error": f"Invalid content type: {content_type}"}

    try:
        start, end = parse_date_range(period)
    except ValueError as e:
        return {"error": str(e)}

    filters = {
        "content_type": ct,
        "timestamp__gte": start,
        "timestamp__lte": end,
    }
    if object_id is not None:
        filters["object_id"] = object_id

    events = PageViewEvent.objects.filter(**filters)

    hourly_data = (
        events.annotate(hour=ExtractHour("timestamp"))
        .values("hour")
        .annotate(count=Count("id"))
    )
    counter = {entry["hour"]: entry["count"] for entry in hourly_data}

    total_views = sum(counter.values())

    # Build all 24 hours
    hours = []
    for h in range(24):
        hours.append(
            {
                "hour": h,
                "label": f"{h:02d}:00",
                "views": counter.get(h, 0),
            }
        )

    # Find peak hour
    if total_views > 0:
        peak = max(range(24), key=lambda h: counter.get(h, 0))
        peak_hour = f"{peak:02d}:00"
    else:
        peak_hour = "00:00"

    return {
        "content_type": content_type,
        "object_id": object_id,
        "period": period,
        "total_views": total_views,
        "peak_hour": peak_hour,
        "hours": hours,
    }
