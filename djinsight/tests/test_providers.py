"""Tests for djinsight providers."""

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from djinsight.models import PageViewEvent, PageViewStatistics
from djinsight.providers.database import AsyncDatabaseProvider, DatabaseProvider
from djinsight.registry import ProviderRegistry


class DatabaseProviderTest(TestCase):
    """Test DatabaseProvider functionality."""

    def setUp(self):
        """Set up test data."""
        self.provider = DatabaseProvider()
        self.content_type = ContentType.objects.get_for_model(PageViewStatistics)

    def test_record_view_creates_event(self):
        """Test that record_view creates a PageViewEvent."""
        event_data = {
            "content_type": f"{self.content_type.app_label}.{self.content_type.model}",
            "object_id": 1,
            "url": "/test/",
            "session_key": "test-session",
            "ip_address": "127.0.0.1",
            "user_agent": "Test Agent",
            "referrer": "https://example.com",
            "timestamp": timezone.now().timestamp(),
            "is_unique": True,
        }

        result = self.provider.record_view(event_data)

        self.assertTrue(result["success"])
        self.assertIn("event_id", result)
        self.assertIn("stats", result)

        # Verify event was created
        event = PageViewEvent.objects.get(id=result["event_id"])
        self.assertEqual(event.object_id, 1)
        self.assertEqual(event.session_key, "test-session")
        self.assertTrue(event.is_unique)

    def test_record_view_updates_statistics(self):
        """Test that record_view updates PageViewStatistics."""
        event_data = {
            "content_type": f"{self.content_type.app_label}.{self.content_type.model}",
            "object_id": 1,
            "url": "/test/",
            "session_key": "test-session",
            "timestamp": timezone.now().timestamp(),
            "is_unique": True,
        }

        result = self.provider.record_view(event_data)

        stats = PageViewStatistics.objects.get(
            content_type=self.content_type, object_id=1
        )
        self.assertEqual(stats.total_views, 1)
        self.assertEqual(stats.unique_views, 1)
        self.assertIsNotNone(stats.first_viewed_at)
        self.assertIsNotNone(stats.last_viewed_at)

    def test_record_view_increments_counts(self):
        """Test that multiple views increment counts correctly."""
        event_data = {
            "content_type": f"{self.content_type.app_label}.{self.content_type.model}",
            "object_id": 1,
            "url": "/test/",
            "session_key": "test-session",
            "timestamp": timezone.now().timestamp(),
            "is_unique": True,
        }

        # First view (unique)
        self.provider.record_view(event_data)

        # Second view (not unique)
        event_data["is_unique"] = False
        event_data["session_key"] = "test-session-2"
        self.provider.record_view(event_data)

        stats = PageViewStatistics.objects.get(
            content_type=self.content_type, object_id=1
        )
        self.assertEqual(stats.total_views, 2)
        self.assertEqual(stats.unique_views, 1)

    def test_get_stats_returns_correct_data(self):
        """Test that get_stats returns correct statistics."""
        # Create some stats
        stats = PageViewStatistics.objects.create(
            content_type=self.content_type,
            object_id=1,
            total_views=10,
            unique_views=5,
            first_viewed_at=timezone.now(),
            last_viewed_at=timezone.now(),
        )

        result = self.provider.get_stats(
            f"{self.content_type.app_label}.{self.content_type.model}", 1
        )

        self.assertEqual(result["total_views"], 10)
        self.assertEqual(result["unique_views"], 5)
        self.assertIsNotNone(result["first_viewed_at"])
        self.assertIsNotNone(result["last_viewed_at"])

    def test_get_stats_returns_zero_for_nonexistent(self):
        """Test that get_stats returns zeros for non-existent object."""
        result = self.provider.get_stats(
            f"{self.content_type.app_label}.{self.content_type.model}", 999
        )

        self.assertEqual(result["total_views"], 0)
        self.assertEqual(result["unique_views"], 0)
        self.assertIsNone(result["first_viewed_at"])
        self.assertIsNone(result["last_viewed_at"])

    def test_check_unique_view_returns_true_for_new_session(self):
        """Test that check_unique_view returns True for new session."""
        is_unique = self.provider.check_unique_view(
            "new-session",
            f"{self.content_type.app_label}.{self.content_type.model}",
            1,
        )

        self.assertTrue(is_unique)

    def test_check_unique_view_returns_false_for_existing_session(self):
        """Test that check_unique_view returns False for existing session."""
        # Create an existing event
        PageViewEvent.objects.create(
            content_type=self.content_type,
            object_id=1,
            session_key="existing-session",
            url="/test/",
        )

        is_unique = self.provider.check_unique_view(
            "existing-session",
            f"{self.content_type.app_label}.{self.content_type.model}",
            1,
        )

        self.assertFalse(is_unique)


class AsyncDatabaseProviderTest(TestCase):
    """Test AsyncDatabaseProvider functionality."""

    def setUp(self):
        """Set up test data."""
        self.provider = AsyncDatabaseProvider()
        self.content_type = ContentType.objects.get_for_model(PageViewStatistics)

    def test_async_provider_instance(self):
        """Test that AsyncDatabaseProvider can be instantiated."""
        self.assertIsInstance(self.provider, AsyncDatabaseProvider)
        self.assertIsInstance(self.provider._sync_provider, DatabaseProvider)


class ProviderRegistryTest(TestCase):
    """Test ProviderRegistry functionality."""

    def test_get_provider_returns_sync_by_default(self):
        """Test that get_provider returns sync provider by default."""
        provider = ProviderRegistry.get_provider()
        self.assertIsInstance(provider, DatabaseProvider)

    def test_get_provider_returns_async_when_requested(self):
        """Test that get_provider returns async provider when requested."""
        provider = ProviderRegistry.get_provider(use_async=True)
        self.assertIsInstance(provider, AsyncDatabaseProvider)

    def test_get_async_provider_convenience_method(self):
        """Test get_async_provider convenience method."""
        provider = ProviderRegistry.get_async_provider()
        self.assertIsInstance(provider, AsyncDatabaseProvider)
