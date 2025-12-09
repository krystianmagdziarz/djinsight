from datetime import datetime
from typing import Any, Dict

from asgiref.sync import sync_to_async
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from djinsight.models import PageViewEvent, PageViewStatistics
from djinsight.providers.base import AsyncBaseProvider, BaseProvider


class DatabaseProvider(BaseProvider):
    """
    Synchronous database provider.
    Writes page views directly to database without Redis buffering.
    Use when you don't want Redis/Celery dependencies.
    """

    def record_view(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Record a page view directly to database."""
        try:
            content_type_str = event_data.get("content_type")
            object_id = event_data.get("object_id")

            app_label, model = content_type_str.split(".")
            ct = ContentType.objects.get_by_natural_key(app_label, model.lower())

            timestamp = event_data.get("timestamp")
            if isinstance(timestamp, (int, float)):
                timestamp = datetime.fromtimestamp(
                    timestamp, tz=timezone.get_current_timezone()
                )
            elif not timestamp:
                timestamp = timezone.now()

            event = PageViewEvent.objects.create(
                content_type=ct,
                object_id=object_id,
                url=event_data.get("url", ""),
                session_key=event_data.get("session_key", "")[:255],
                ip_address=event_data.get("ip_address", ""),
                user_agent=event_data.get("user_agent", "")[:1000],
                referrer=event_data.get("referrer", "")[:500],
                timestamp=timestamp,
                is_unique=event_data.get("is_unique", False),
            )

            stats, created = PageViewStatistics.objects.get_or_create(
                content_type=ct,
                object_id=object_id,
            )

            stats.total_views += 1
            if event_data.get("is_unique"):
                stats.unique_views += 1

            stats.last_viewed_at = timezone.now()
            if not stats.first_viewed_at:
                stats.first_viewed_at = timezone.now()

            stats.save(
                update_fields=[
                    "total_views",
                    "unique_views",
                    "last_viewed_at",
                    "first_viewed_at",
                ]
            )

            return {
                "success": True,
                "event_id": event.id,
                "stats": {
                    "total_views": stats.total_views,
                    "unique_views": stats.unique_views,
                },
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_stats(self, content_type: str, object_id: int) -> Dict[str, Any]:
        """Get statistics from database."""
        try:
            app_label, model = content_type.split(".")
            ct = ContentType.objects.get_by_natural_key(app_label, model.lower())

            stats = PageViewStatistics.objects.filter(
                content_type=ct, object_id=object_id
            ).first()

            if not stats:
                return {
                    "total_views": 0,
                    "unique_views": 0,
                    "first_viewed_at": None,
                    "last_viewed_at": None,
                }

            return {
                "total_views": stats.total_views,
                "unique_views": stats.unique_views,
                "first_viewed_at": stats.first_viewed_at.isoformat()
                if stats.first_viewed_at
                else None,
                "last_viewed_at": stats.last_viewed_at.isoformat()
                if stats.last_viewed_at
                else None,
            }

        except Exception as e:
            return {"error": str(e)}

    def check_unique_view(
        self, session_key: str, content_type: str, object_id: int
    ) -> bool:
        """Check if this is a unique view by checking existing events."""
        try:
            app_label, model = content_type.split(".")
            ct = ContentType.objects.get_by_natural_key(app_label, model.lower())

            exists = PageViewEvent.objects.filter(
                content_type=ct,
                object_id=object_id,
                session_key=session_key,
            ).exists()

            return not exists
        except Exception:
            return True

    def increment_counter(self, key: str, amount: int = 1) -> int:
        """Not used in database provider - stats are updated directly."""
        return amount

    def mark_viewed(
        self, session_key: str, content_type: str, object_id: int, ttl: int = 86400
    ) -> None:
        """Not needed for database provider - uniqueness tracked via PageViewEvent."""
        pass


class AsyncDatabaseProvider(AsyncBaseProvider):
    """
    Asynchronous database provider.
    Wraps DatabaseProvider methods with sync_to_async for use in async views.
    Use when you need async support without Redis.
    """

    def __init__(self):
        self._sync_provider = DatabaseProvider()

    async def record_view(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Record a page view asynchronously."""
        return await sync_to_async(
            self._sync_provider.record_view, thread_sensitive=True
        )(event_data)

    async def get_stats(self, content_type: str, object_id: int) -> Dict[str, Any]:
        """Get statistics asynchronously."""
        return await sync_to_async(
            self._sync_provider.get_stats, thread_sensitive=True
        )(content_type, object_id)

    async def check_unique_view(
        self, session_key: str, content_type: str, object_id: int
    ) -> bool:
        """Check if this is a unique view asynchronously."""
        return await sync_to_async(
            self._sync_provider.check_unique_view, thread_sensitive=True
        )(session_key, content_type, object_id)

    async def increment_counter(self, key: str, amount: int = 1) -> int:
        """Not used in database provider."""
        return amount

    async def mark_viewed(
        self, session_key: str, content_type: str, object_id: int, ttl: int = 86400
    ) -> None:
        """Not needed for database provider."""
        pass
