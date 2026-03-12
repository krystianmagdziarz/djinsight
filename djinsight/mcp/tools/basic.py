"""Basic MCP tools for djinsight."""

import logging
from typing import Dict

from django.contrib.contenttypes.models import ContentType

from djinsight.mcp.utils import parse_content_type_str
from djinsight.models import ContentTypeRegistry, PageViewStatistics

logger = logging.getLogger(__name__)


def get_page_stats(content_type: str, object_id: int) -> Dict:
    """Get page view statistics for a specific object.

    Args:
        content_type: Content type string in 'app_label.model' format.
        object_id: The primary key of the object.

    Returns:
        Dict with content_type, object_id, object, total_views, unique_views,
        first_viewed_at, last_viewed_at. Returns error dict for invalid content type.
        Returns zeros if no stats found.
    """
    ct = parse_content_type_str(content_type)
    if not ct:
        return {"error": f"Invalid content type: {content_type}"}

    # Try to get the actual object for its string representation
    obj_str = None
    try:
        model_class = ct.model_class()
        obj = model_class.objects.get(pk=object_id)
        obj_str = str(obj)
    except Exception:
        obj_str = None

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
        "first_viewed_at": (
            stats.first_viewed_at.isoformat() if stats.first_viewed_at else None
        ),
        "last_viewed_at": (
            stats.last_viewed_at.isoformat() if stats.last_viewed_at else None
        ),
    }


def get_top_pages(
    content_type: str, limit: int = 10, metric: str = "total_views"
) -> Dict:
    """Get top pages sorted by metric.

    Args:
        content_type: Content type string in 'app_label.model' format.
        limit: Number of results to return (default 10).
        metric: Metric to sort by, 'total_views' or 'unique_views'.

    Returns:
        Dict with content_type, metric, and results list. Each result contains
        object_id, object, total_views, unique_views, last_viewed_at.
    """
    ct = parse_content_type_str(content_type)
    if not ct:
        return {"error": f"Invalid content type: {content_type}"}

    ALLOWED_METRICS = {"total_views", "unique_views"}
    if metric not in ALLOWED_METRICS:
        return {"error": f"Invalid metric: {metric}. Must be one of: {', '.join(sorted(ALLOWED_METRICS))}"}

    limit = min(max(1, limit), 100)

    stats = PageViewStatistics.objects.filter(content_type=ct).order_by(f"-{metric}")[
        :limit
    ]

    # Batch-load object names for efficiency
    model_class = ct.model_class()
    object_ids = [s.object_id for s in stats]
    objects_dict = {}

    try:
        objects = model_class.objects.filter(pk__in=object_ids)
        objects_dict = {obj.pk: str(obj) for obj in objects}
    except Exception:
        logger.warning("Could not fetch objects for top pages")

    return {
        "content_type": content_type,
        "metric": metric,
        "results": [
            {
                "object_id": s.object_id,
                "object": objects_dict.get(s.object_id),
                "total_views": s.total_views,
                "unique_views": s.unique_views,
                "last_viewed_at": (
                    s.last_viewed_at.isoformat() if s.last_viewed_at else None
                ),
            }
            for s in stats
        ],
    }


def list_tracked_models() -> Dict:
    """List all enabled ContentTypeRegistry entries.

    Returns:
        Dict with tracked_models list. Each entry contains app_label, model,
        content_type, track_anonymous, track_authenticated.
    """
    registries = ContentTypeRegistry.objects.filter(enabled=True).select_related(
        "content_type"
    )

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
