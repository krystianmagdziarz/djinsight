"""Tests for djinsight views."""

import json

from django.contrib.contenttypes.models import ContentType
from django.test import Client, TestCase
from django.urls import reverse

from djinsight.models import PageViewStatistics


class RecordPageViewTest(TestCase):
    """Test record_page_view endpoint."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.content_type = ContentType.objects.get_for_model(PageViewStatistics)

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
