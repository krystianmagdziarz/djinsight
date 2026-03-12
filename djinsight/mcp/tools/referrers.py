"""Referrer analytics tools for the djinsight MCP server."""

from collections import Counter

from djinsight.mcp.utils import (
    classify_referrer,
    extract_domain,
    parse_content_type_str,
    parse_date_range,
)
from djinsight.models import PageViewEvent


def get_referrer_stats(content_type, object_id=None, period="month", limit=20):
    """Get top referrers grouped by domain.

    Args:
        content_type: 'app_label.model' string.
        object_id: Optional object ID to filter by.
        period: One of 'today', 'week', 'month', 'year'.
        limit: Maximum number of referrer domains to return.

    Returns:
        Dict with content_type, object_id, period, total_referrals,
        and referrers list (domain, views).
    """
    limit = min(max(1, limit), 100)

    ct = parse_content_type_str(content_type)
    if ct is None:
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

    domain_counter = Counter()
    for referrer in events.values_list("referrer", flat=True).iterator():
        domain = extract_domain(referrer)
        domain_counter[domain] += 1

    total_referrals = sum(domain_counter.values())
    top_referrers = [
        {"domain": domain, "views": views}
        for domain, views in domain_counter.most_common(limit)
    ]

    return {
        "content_type": content_type,
        "object_id": object_id,
        "period": period,
        "total_referrals": total_referrals,
        "referrers": top_referrers,
    }


def get_traffic_sources(content_type, object_id=None, period="month"):
    """Aggregate page views by traffic source category.

    Args:
        content_type: 'app_label.model' string.
        object_id: Optional object ID to filter by.
        period: One of 'today', 'week', 'month', 'year'.

    Returns:
        Dict with content_type, object_id, period, total_views,
        and sources list (source, views, percentage).
    """
    ct = parse_content_type_str(content_type)
    if ct is None:
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

    source_counter = Counter()
    for referrer in events.values_list("referrer", flat=True).iterator():
        source = classify_referrer(referrer)
        source_counter[source] += 1

    total_views = sum(source_counter.values())
    sources = []
    for source, views in source_counter.most_common():
        percentage = round((views / total_views) * 100, 1) if total_views > 0 else 0.0
        sources.append(
            {
                "source": source,
                "views": views,
                "percentage": percentage,
            }
        )

    return {
        "content_type": content_type,
        "object_id": object_id,
        "period": period,
        "total_views": total_views,
        "sources": sources,
    }
