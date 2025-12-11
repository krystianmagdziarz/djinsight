import json
import logging
from typing import Any, Dict, Optional

from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from djinsight.models import MCPAPIKey, PageViewStatistics, StatsQueryMixin

logger = logging.getLogger(__name__)


class MCPServer:
    """
    Model Context Protocol server for djinsight.
    Exposes Django app statistics to AI agents through MCP.
    """

    @staticmethod
    def get_tools():
        """Return available MCP tools."""
        return [
            {
                "name": "get_page_stats",
                "description": "Get page view statistics for a specific object",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content_type": {
                            "type": "string",
                            "description": "Content type in format 'app_label.model' (e.g., 'blog.post')",
                        },
                        "object_id": {"type": "number", "description": "Object ID"},
                    },
                    "required": ["content_type", "object_id"],
                },
            },
            {
                "name": "get_top_pages",
                "description": "Get top performing pages by views",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content_type": {
                            "type": "string",
                            "description": "Content type in format 'app_label.model' (e.g., 'blog.Article')",
                        },
                        "limit": {
                            "type": "number",
                            "description": "Number of results to return (default: 10)",
                        },
                        "metric": {
                            "type": "string",
                            "enum": ["total_views", "unique_views"],
                            "description": "Metric to sort by (default: total_views)",
                        },
                    },
                    "required": ["content_type"],
                },
            },
            {
                "name": "get_period_stats",
                "description": "Get statistics for a specific time period",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content_type": {
                            "type": "string",
                            "description": "Content type in format 'app_label.model'",
                        },
                        "object_id": {"type": "number", "description": "Object ID"},
                        "period": {
                            "type": "string",
                            "enum": ["today", "week", "month", "year"],
                            "description": "Time period",
                        },
                    },
                    "required": ["content_type", "object_id", "period"],
                },
            },
            {
                "name": "list_tracked_models",
                "description": "List all content types that are being tracked",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]

    @staticmethod
    def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an MCP tool."""
        try:
            if tool_name == "get_page_stats":
                return MCPServer._get_page_stats(arguments)
            elif tool_name == "get_top_pages":
                return MCPServer._get_top_pages(arguments)
            elif tool_name == "get_period_stats":
                return MCPServer._get_period_stats(arguments)
            elif tool_name == "list_tracked_models":
                return MCPServer._list_tracked_models(arguments)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {"error": str(e)}

    @staticmethod
    def _parse_content_type(content_type_str: str) -> Optional[ContentType]:
        """Parse content type string 'app_label.model' into ContentType."""
        try:
            app_label, model = content_type_str.split(".")
            return ContentType.objects.get(app_label=app_label, model=model.lower())
        except (ValueError, ContentType.DoesNotExist) as e:
            logger.error(f"Invalid content type: {content_type_str} - {e}")
            return None

    @staticmethod
    def _get_page_stats(arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get statistics for a specific page."""
        content_type_str = arguments.get("content_type")
        object_id = arguments.get("object_id")

        ct = MCPServer._parse_content_type(content_type_str)
        if not ct:
            return {"error": f"Invalid content type: {content_type_str}"}

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
                "content_type": content_type_str,
                "object_id": object_id,
                "object": obj_str,
                "total_views": 0,
                "unique_views": 0,
                "first_viewed_at": None,
                "last_viewed_at": None,
            }

        return {
            "content_type": content_type_str,
            "object_id": object_id,
            "object": obj_str,
            "total_views": stats.total_views,
            "unique_views": stats.unique_views,
            "first_viewed_at": stats.first_viewed_at.isoformat()
            if stats.first_viewed_at
            else None,
            "last_viewed_at": stats.last_viewed_at.isoformat()
            if stats.last_viewed_at
            else None,
        }

    @staticmethod
    def _get_top_pages(arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get top performing pages."""
        content_type_str = arguments.get("content_type")
        limit = arguments.get("limit", 10)
        metric = arguments.get("metric", "total_views")

        ct = MCPServer._parse_content_type(content_type_str)
        if not ct:
            return {"error": f"Invalid content type: {content_type_str}"}

        stats = PageViewStatistics.objects.filter(content_type=ct).order_by(
            f"-{metric}"
        )[:limit]

        # Get all objects at once for efficiency
        model_class = ct.model_class()
        object_ids = [s.object_id for s in stats]
        objects_dict = {}

        try:
            objects = model_class.objects.filter(pk__in=object_ids)
            objects_dict = {obj.pk: str(obj) for obj in objects}
        except Exception as e:
            logger.warning(f"Could not fetch objects for top pages: {e}")

        return {
            "content_type": content_type_str,
            "metric": metric,
            "results": [
                {
                    "object_id": s.object_id,
                    "object": objects_dict.get(s.object_id),
                    "total_views": s.total_views,
                    "unique_views": s.unique_views,
                    "last_viewed_at": s.last_viewed_at.isoformat()
                    if s.last_viewed_at
                    else None,
                }
                for s in stats
            ],
        }

    @staticmethod
    def _get_period_stats(arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get statistics for a time period."""
        content_type_str = arguments.get("content_type")
        object_id = arguments.get("object_id")
        period = arguments.get("period", "week")

        ct = MCPServer._parse_content_type(content_type_str)
        if not ct:
            return {"error": f"Invalid content type: {content_type_str}"}

        try:
            model_class = ct.model_class()
            obj = model_class.objects.get(pk=object_id)
            obj_str = str(obj)
        except Exception as e:
            return {"error": f"Object not found: {e}"}

        period_map = {
            "today": StatsQueryMixin.get_views_today,
            "week": StatsQueryMixin.get_views_week,
            "month": StatsQueryMixin.get_views_month,
            "year": StatsQueryMixin.get_views_year,
        }

        handler = period_map.get(period)
        if not handler:
            return {"error": f"Invalid period: {period}"}

        views = handler(obj, chart_data=True)

        return {
            "content_type": content_type_str,
            "object_id": object_id,
            "object": obj_str,
            "period": period,
            "data": views,
        }

    @staticmethod
    def _list_tracked_models(arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all tracked content types."""
        from djinsight.models import ContentTypeRegistry

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


@csrf_exempt
@require_http_methods(["POST"])
def mcp_endpoint(request):
    """Main MCP endpoint."""
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JsonResponse(
                {"error": "Missing or invalid Authorization header"}, status=401
            )

        api_key = auth_header[7:]
        if not MCPAPIKey.validate_key(api_key):
            return JsonResponse({"error": "Invalid API key"}, status=403)

        data = json.loads(request.body)
        action = data.get("action")

        if action == "list_tools":
            tools = MCPServer.get_tools()
            return JsonResponse({"tools": tools})

        elif action == "execute_tool":
            tool_name = data.get("tool_name")
            arguments = data.get("arguments", {})

            result = MCPServer.execute_tool(tool_name, arguments)
            return JsonResponse(result)

        else:
            return JsonResponse({"error": "Invalid action"}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"MCP endpoint error: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)
