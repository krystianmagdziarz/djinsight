"""Tests for djinsight models."""

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from djinsight.models import (
    ContentTypeRegistry,
    MCPAPIKey,
    PageViewEvent,
    PageViewStatistics,
    PageViewSummary,
)


class ContentTypeRegistryTest(TestCase):
    """Test ContentTypeRegistry model."""

    def setUp(self):
        """Set up test data."""
        self.content_type = ContentType.objects.get_for_model(PageViewStatistics)

    def test_register_creates_entry(self):
        """Test that register creates a ContentTypeRegistry entry."""
        ContentTypeRegistry.register(PageViewStatistics)

        registry = ContentTypeRegistry.objects.get(content_type=self.content_type)
        self.assertTrue(registry.enabled)
        self.assertTrue(registry.track_anonymous)
        self.assertTrue(registry.track_authenticated)

    def test_register_with_custom_settings(self):
        """Test register with custom settings."""
        ContentTypeRegistry.register(
            PageViewStatistics,
            track_anonymous=False,
            track_authenticated=True,
        )

        registry = ContentTypeRegistry.objects.get(content_type=self.content_type)
        self.assertFalse(registry.track_anonymous)
        self.assertTrue(registry.track_authenticated)

    def test_is_tracked_returns_true_for_registered(self):
        """Test is_tracked returns True for registered model."""
        ContentTypeRegistry.register(PageViewStatistics)

        obj = PageViewStatistics.objects.create(
            content_type=self.content_type, object_id=1
        )
        self.assertTrue(ContentTypeRegistry.is_tracked(obj))

    def test_is_tracked_returns_false_for_unregistered(self):
        """Test is_tracked returns False for unregistered model."""
        obj = PageViewStatistics.objects.create(
            content_type=self.content_type, object_id=1
        )
        self.assertFalse(ContentTypeRegistry.is_tracked(obj))

    def test_is_tracked_returns_false_for_disabled(self):
        """Test is_tracked returns False for disabled registry."""
        ContentTypeRegistry.register(PageViewStatistics)
        registry = ContentTypeRegistry.objects.get(content_type=self.content_type)
        registry.enabled = False
        registry.save()

        obj = PageViewStatistics.objects.create(
            content_type=self.content_type, object_id=1
        )
        self.assertFalse(ContentTypeRegistry.is_tracked(obj))


class PageViewEventTest(TestCase):
    """Test PageViewEvent model."""

    def setUp(self):
        """Set up test data."""
        self.content_type = ContentType.objects.get_for_model(PageViewStatistics)

    def test_create_event(self):
        """Test creating a PageViewEvent."""
        event = PageViewEvent.objects.create(
            content_type=self.content_type,
            object_id=1,
            url="/test/",
            session_key="test-session",
            ip_address="127.0.0.1",
            user_agent="Test Agent",
            referrer="https://example.com",
            is_unique=True,
        )

        self.assertEqual(event.object_id, 1)
        self.assertEqual(event.url, "/test/")
        self.assertEqual(event.session_key, "test-session")
        self.assertTrue(event.is_unique)
        self.assertIsNotNone(event.timestamp)

    def test_event_str_representation(self):
        """Test string representation of PageViewEvent."""
        event = PageViewEvent.objects.create(
            content_type=self.content_type,
            object_id=1,
            url="/test/",
        )

        # Format: "{content_type} #{object_id} at {timestamp}"
        self.assertIn(str(self.content_type), str(event))
        self.assertIn("#1", str(event))
        self.assertIn("at", str(event))


class PageViewStatisticsTest(TestCase):
    """Test PageViewStatistics model."""

    def setUp(self):
        """Set up test data."""
        self.content_type = ContentType.objects.get_for_model(PageViewStatistics)

    def test_create_statistics(self):
        """Test creating PageViewStatistics."""
        stats = PageViewStatistics.objects.create(
            content_type=self.content_type,
            object_id=1,
            total_views=10,
            unique_views=5,
        )

        self.assertEqual(stats.total_views, 10)
        self.assertEqual(stats.unique_views, 5)
        self.assertIsNone(stats.first_viewed_at)
        self.assertIsNone(stats.last_viewed_at)

    def test_get_for_object(self):
        """Test get_for_object class method."""
        # Create stats for PageViewStatistics model itself
        stats = PageViewStatistics.objects.create(
            content_type=self.content_type,
            object_id=1,
            total_views=10,
        )

        # Use the stats object itself as test object
        retrieved = PageViewStatistics.get_for_object(stats)
        self.assertIsNotNone(retrieved)
        # Should find stats for PageViewStatistics with same pk
        self.assertEqual(retrieved.object_id, stats.pk)

    def test_stats_str_representation(self):
        """Test string representation of PageViewStatistics."""
        stats = PageViewStatistics.objects.create(
            content_type=self.content_type,
            object_id=1,
            total_views=10,
        )

        # Format: "{content_type} #{object_id}: {total_views} views"
        self.assertIn(str(self.content_type), str(stats))
        self.assertIn("#1", str(stats))
        self.assertIn("10 views", str(stats))


class PageViewSummaryTest(TestCase):
    """Test PageViewSummary model."""

    def setUp(self):
        """Set up test data."""
        self.content_type = ContentType.objects.get_for_model(PageViewStatistics)

    def test_create_summary(self):
        """Test creating a PageViewSummary."""
        today = timezone.now().date()
        summary = PageViewSummary.objects.create(
            content_type=self.content_type,
            object_id=1,
            date=today,
            total_views=100,
            unique_views=75,
        )

        self.assertEqual(summary.total_views, 100)
        self.assertEqual(summary.unique_views, 75)
        self.assertEqual(summary.date, today)

    def test_summary_str_representation(self):
        """Test string representation of PageViewSummary."""
        today = timezone.now().date()
        summary = PageViewSummary.objects.create(
            content_type=self.content_type,
            object_id=1,
            date=today,
            total_views=100,
        )

        # Format: "{content_type} #{object_id} - {date}: {total_views} views"
        self.assertIn(str(self.content_type), str(summary))
        self.assertIn("#1", str(summary))
        self.assertIn(str(today), str(summary))
        self.assertIn("100 views", str(summary))


class MCPAPIKeyTest(TestCase):
    """Test MCPAPIKey model."""

    def test_create_key(self):
        """Test creating an API key."""
        key = MCPAPIKey.create_key("test-key", "Test description")

        self.assertEqual(key.name, "test-key")
        self.assertEqual(key.description, "Test description")
        self.assertTrue(key.is_active)
        self.assertIsNotNone(key.key)
        self.assertEqual(len(key.key), 64)

    def test_validate_key_returns_true_for_valid(self):
        """Test validate_key returns True for valid key."""
        key = MCPAPIKey.create_key("test-key")
        self.assertTrue(MCPAPIKey.validate_key(key.key))

    def test_validate_key_returns_false_for_invalid(self):
        """Test validate_key returns False for invalid key."""
        self.assertFalse(MCPAPIKey.validate_key("invalid-key"))

    def test_validate_key_returns_false_for_inactive(self):
        """Test validate_key returns False for inactive key."""
        key = MCPAPIKey.create_key("test-key")
        key.is_active = False
        key.save()

        self.assertFalse(MCPAPIKey.validate_key(key.key))

    def test_validate_key_updates_last_used(self):
        """Test that validate_key updates last_used_at."""
        key = MCPAPIKey.create_key("test-key")
        original_last_used = key.last_used_at

        MCPAPIKey.validate_key(key.key)

        key.refresh_from_db()
        self.assertIsNotNone(key.last_used_at)
        if original_last_used:
            self.assertGreater(key.last_used_at, original_last_used)

    def test_generate_key_creates_unique_key(self):
        """Test that generate_key creates unique keys."""
        key1 = MCPAPIKey.generate_key()
        key2 = MCPAPIKey.generate_key()

        self.assertNotEqual(key1, key2)
        self.assertEqual(len(key1), 64)
        self.assertEqual(len(key2), 64)
