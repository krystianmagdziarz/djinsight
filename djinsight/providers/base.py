from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseProvider(ABC):
    """
    Base provider interface for djinsight.
    Implementations can be sync or async depending on use case.
    """

    @abstractmethod
    def record_view(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Record a page view event."""
        pass

    @abstractmethod
    def get_stats(self, content_type: str, object_id: int) -> Dict[str, Any]:
        """Get statistics for an object."""
        pass

    @abstractmethod
    def check_unique_view(
        self, session_key: str, content_type: str, object_id: int
    ) -> bool:
        """Check if this is a unique view for the session."""
        pass

    @abstractmethod
    def increment_counter(self, key: str, amount: int = 1) -> int:
        """Increment a counter (used by Redis provider)."""
        pass

    @abstractmethod
    def mark_viewed(
        self, session_key: str, content_type: str, object_id: int, ttl: int = 86400
    ) -> None:
        """Mark object as viewed by session (used by Redis provider)."""
        pass


class AsyncBaseProvider(ABC):
    """
    Async base provider interface for djinsight.
    Use this for async Django views or when using async database backends.
    """

    @abstractmethod
    async def record_view(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Record a page view event asynchronously."""
        pass

    @abstractmethod
    async def get_stats(self, content_type: str, object_id: int) -> Dict[str, Any]:
        """Get statistics for an object asynchronously."""
        pass

    @abstractmethod
    async def check_unique_view(
        self, session_key: str, content_type: str, object_id: int
    ) -> bool:
        """Check if this is a unique view for the session asynchronously."""
        pass

    @abstractmethod
    async def increment_counter(self, key: str, amount: int = 1) -> int:
        """Increment a counter asynchronously."""
        pass

    @abstractmethod
    async def mark_viewed(
        self, session_key: str, content_type: str, object_id: int, ttl: int = 86400
    ) -> None:
        """Mark object as viewed by session asynchronously."""
        pass
