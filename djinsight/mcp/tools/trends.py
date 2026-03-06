"""Trending pages tool for djinsight MCP server."""

from django.db.models import Count

from djinsight.mcp.utils import parse_content_type_str, parse_date_range
from djinsight.models import PageViewEvent


def get_trending_pages(content_type, period="week", direction="up", limit=10):
    """Get pages with biggest growth or decline compared to previous period.

    Args:
        content_type: String in 'app_label.model' format.
        period: One of 'today', 'week', 'month', 'year'.
        direction: 'up' for growing pages, 'down' for declining pages.
        limit: Maximum number of results to return.

    Returns:
        Dict with content_type, period, direction, and results list.
    """
    ct = parse_content_type_str(content_type)
    if ct is None:
        return {
            "content_type": content_type,
            "period": period,
            "direction": direction,
            "error": f"Invalid content type: {content_type}",
            "results": [],
        }

    # Step 1: Get current period date range
    current_start, current_end = parse_date_range(period)

    # Step 2: Calculate previous period (same duration, shifted back)
    duration = current_end - current_start
    previous_start = current_start - duration
    previous_end = current_start

    # Step 3: Count views per object_id in both periods
    current_counts = dict(
        PageViewEvent.objects.filter(
            content_type=ct,
            timestamp__gte=current_start,
            timestamp__lte=current_end,
        )
        .values("object_id")
        .annotate(view_count=Count("id"))
        .values_list("object_id", "view_count")
    )

    previous_counts = dict(
        PageViewEvent.objects.filter(
            content_type=ct,
            timestamp__gte=previous_start,
            timestamp__lt=previous_end,
        )
        .values("object_id")
        .annotate(view_count=Count("id"))
        .values_list("object_id", "view_count")
    )

    # Merge all object_ids from both periods
    all_object_ids = set(current_counts.keys()) | set(previous_counts.keys())

    # Step 4: Compute growth_rate for each object
    results = []
    for object_id in all_object_ids:
        curr = current_counts.get(object_id, 0)
        prev = previous_counts.get(object_id, 0)
        delta = curr - prev

        if prev == 0:
            growth_rate = 100.0 if curr > 0 else 0.0
        else:
            growth_rate = round((curr - prev) / prev * 100, 2)

        # Skip objects with no change if not relevant
        results.append(
            {
                "object_id": object_id,
                "current_views": curr,
                "previous_views": prev,
                "growth_rate": growth_rate,
                "delta": delta,
            }
        )

    # Step 5: Sort by growth_rate
    reverse = direction == "up"
    results.sort(key=lambda r: r["growth_rate"], reverse=reverse)

    # Step 6: Limit and resolve object names
    results = results[:limit]

    # Resolve object names
    model_class = ct.model_class()
    if model_class is not None:
        object_ids = [r["object_id"] for r in results]
        objects = {
            obj.pk: str(obj) for obj in model_class.objects.filter(pk__in=object_ids)
        }
        for r in results:
            r["object"] = objects.get(r["object_id"], f"#{r['object_id']}")
    else:
        for r in results:
            r["object"] = f"#{r['object_id']}"

    return {
        "content_type": content_type,
        "period": period,
        "direction": direction,
        "results": results,
    }
