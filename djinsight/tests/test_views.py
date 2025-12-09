"""Tests for djinsight views."""

import json

from django.contrib.contenttypes.models import ContentType
from django.test import Client, TestCase
from django.urls import reverse

from djinsight.models import ContentTypeRegistry, MCPAPIKey, PageViewStatistics


class RecordPageViewTest(TestCase):
    """Test record_page_view endpoint."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.content_type = ContentType.objects.get_for_model(PageViewStatistics)
        ContentTypeRegistry.register(PageViewStatistics)

    def test_record_view_creates_event(self):
        """Test that posting to record_page_view creates an event."""
        data = {
            "content_type": f"{self.content_type.app_label}.{self.content_type.model}",
            "object_id": 1,
            "url": "/test/",
            "referrer": "https://example.com",
            "user_agent": "Test Agent",
        }

        response = self.client.post(
            reverse("djinsight:record_page_view"),
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result.get("success"))

    def test_record_view_requires_object_id(self):
        """Test that object_id is required."""
        data = {
            "content_type": f"{self.content_type.app_label}.{self.content_type.model}",
            "url": "/test/",
        }

        response = self.client.post(
            reverse("djinsight:record_page_view"),
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_record_view_requires_content_type(self):
        """Test that content_type is required."""
        data = {
            "object_id": 1,
            "url": "/test/",
        }

        response = self.client.post(
            reverse("djinsight:record_page_view"),
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_record_view_ignores_unregistered_model(self):
        """Test that unregistered models are ignored."""
        # Unregister the model
        ContentTypeRegistry.objects.filter(content_type=self.content_type).delete()

        data = {
            "content_type": f"{self.content_type.app_label}.{self.content_type.model}",
            "object_id": 1,
            "url": "/test/",
        }

        response = self.client.post(
            reverse("djinsight:record_page_view"),
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result.get("status"), "ignored")


class MCPEndpointTest(TestCase):
    """Test MCP endpoint."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.api_key = MCPAPIKey.create_key("test-key", "Test API key")
        self.content_type = ContentType.objects.get_for_model(PageViewStatistics)
        ContentTypeRegistry.register(PageViewStatistics)

    def test_mcp_requires_auth(self):
        """Test that MCP endpoint requires authentication."""
        response = self.client.post(
            "/djinsight/mcp/",
            data=json.dumps({"action": "list_tools"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)

    def test_mcp_list_tools(self):
        """Test MCP list_tools action."""
        response = self.client.post(
            "/djinsight/mcp/",
            data=json.dumps({"action": "list_tools"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.api_key.key}",
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertIn("tools", result)
        self.assertIsInstance(result["tools"], list)
        self.assertGreater(len(result["tools"]), 0)

    def test_mcp_list_tracked_models(self):
        """Test MCP list_tracked_models tool."""
        response = self.client.post(
            "/djinsight/mcp/",
            data=json.dumps(
                {
                    "action": "execute_tool",
                    "tool_name": "list_tracked_models",
                    "arguments": {},
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.api_key.key}",
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertIn("tracked_models", result)
        self.assertIsInstance(result["tracked_models"], list)

    def test_mcp_get_page_stats(self):
        """Test MCP get_page_stats tool."""
        # Create some stats
        PageViewStatistics.objects.create(
            content_type=self.content_type,
            object_id=1,
            total_views=10,
            unique_views=5,
        )

        response = self.client.post(
            "/djinsight/mcp/",
            data=json.dumps(
                {
                    "action": "execute_tool",
                    "tool_name": "get_page_stats",
                    "arguments": {
                        "content_type": f"{self.content_type.app_label}.{self.content_type.model}",
                        "object_id": 1,
                    },
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.api_key.key}",
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["total_views"], 10)
        self.assertEqual(result["unique_views"], 5)

    def test_mcp_invalid_api_key(self):
        """Test MCP with invalid API key."""
        response = self.client.post(
            "/djinsight/mcp/",
            data=json.dumps({"action": "list_tools"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer invalid-key",
        )

        self.assertEqual(response.status_code, 403)
