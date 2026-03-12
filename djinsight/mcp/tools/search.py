"""Search tools for the djinsight MCP server."""

import logging
from typing import Dict, Optional

from django.contrib.contenttypes.models import ContentType

from djinsight.mcp.utils import parse_content_type_str
from djinsight.models import ContentTypeRegistry, PageViewStatistics

logger = logging.getLogger(__name__)

COMMON_SEARCH_FIELDS = ("title", "name", "headline", "subject")


def search_pages(
    query: str, content_type: Optional[str] = None, limit: int = 20
) -> Dict:
    """Search tracked objects by name/title and return with their stats.

    Args:
        query: Search string to match against object fields (case-insensitive).
        content_type: Optional 'app_label.model' string to restrict search.
        limit: Maximum number of results to return (default 20).

    Returns:
        Dict with query, total_results, and results list. Each result contains
        content_type, object_id, object, total_views, unique_views.
        Returns error dict if query is empty.
    """
    if not query or not isinstance(query, str) or not query.strip():
        return {"error": "Query cannot be empty"}

    query = query.strip()
    limit = min(max(1, limit), 100)

    # Determine which content types to search
    if content_type:
        ct = parse_content_type_str(content_type)
        if not ct:
            return {"error": f"Invalid content type: {content_type}"}
        content_types = [ct]
    else:
        registries = ContentTypeRegistry.objects.filter(enabled=True).select_related(
            "content_type"
        )
        content_types = [r.content_type for r in registries]

    results = []

    for ct in content_types:
        ct_str = f"{ct.app_label}.{ct.model}"
        model_class = ct.model_class()
        if model_class is None:
            continue

        matched_objects = _search_model(model_class, query)

        # Batch-load stats to avoid N+1 queries
        obj_ids = [obj.pk for obj in matched_objects]
        stats_map = {}
        if obj_ids:
            for s in PageViewStatistics.objects.filter(
                content_type=ct, object_id__in=obj_ids
            ):
                stats_map[s.object_id] = s

        for obj in matched_objects:
            stats = stats_map.get(obj.pk)
            results.append(
                {
                    "content_type": ct_str,
                    "object_id": obj.pk,
                    "object": str(obj),
                    "total_views": stats.total_views if stats else 0,
                    "unique_views": stats.unique_views if stats else 0,
                }
            )

    # Sort by total_views descending
    results.sort(key=lambda r: r["total_views"], reverse=True)

    # Apply limit
    results = results[:limit]

    return {
        "query": query,
        "total_results": len(results),
        "results": results,
    }


def _search_model(model_class, query):
    """Search a model for objects matching query.

    Tries common field names first (title, name, headline, subject) with
    icontains lookup. Falls back to filtering by str(obj) if no searchable
    fields are found.

    Returns a list of matched model instances.
    """
    # Try common search fields
    for field_name in COMMON_SEARCH_FIELDS:
        try:
            model_class._meta.get_field(field_name)
        except Exception:
            continue

        # Field exists, use it for filtering
        lookup = {f"{field_name}__icontains": query}
        return list(model_class.objects.filter(**lookup))

    # Fallback: load objects and filter by str representation
    query_lower = query.lower()
    matched = []
    for obj in model_class.objects.all()[:200]:
        if query_lower in str(obj).lower():
            matched.append(obj)
    return matched
