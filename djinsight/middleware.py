import json

from django.template.loader import render_to_string
from django.urls import NoReverseMatch, reverse

from djinsight.conf import djinsight_settings
from djinsight.utils import get_content_type_label, get_object_url


class TrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if not djinsight_settings.ENABLE_TRACKING:
            return response

        if not djinsight_settings.AUTO_INJECT_TRACKING:
            return response

        if not self._should_inject(request, response):
            return response

        tracked_obj = self._find_tracked_object(request)
        if not tracked_obj:
            return response

        tracking_script = self._generate_tracking_script(request, tracked_obj)
        if tracking_script:
            response.content = self._inject_script(response.content, tracking_script)

        return response

    def _should_inject(self, request, response) -> bool:
        if response.status_code != 200:
            return False

        content_type = response.get("Content-Type", "")
        if "text/html" not in content_type:
            return False

        user = getattr(request, "user", None)
        if not djinsight_settings.should_track_user(user):
            return False

        return True

    def _find_tracked_object(self, request):
        """Find object to track. Injects script for any object with pk.
        Actual recording is filtered by ContentTypeRegistry in views."""
        for attr in ["_djinsight_tracked_object", "object", "page"]:
            obj = getattr(request, attr, None)
            if obj and hasattr(obj, "pk") and obj.pk:
                return obj

        return None

    def _generate_tracking_script(self, request, obj) -> str:
        try:
            record_url = reverse("djinsight:record_page_view")
        except NoReverseMatch:
            record_url = "/djinsight/record-view/"

        object_data = json.dumps(
            {
                "object_id": obj.pk,
                "content_type": get_content_type_label(obj),
                "url": get_object_url(obj, request),
            }
        )

        return render_to_string(
            "djinsight/tracking_script.html",
            {
                "object_data": object_data,
                "record_url": record_url,
                "async_load": True,
                "debug": False,
            },
        )

    def _inject_script(self, content: bytes, script: str) -> bytes:
        content_str = content.decode("utf-8")

        if "</body>" in content_str:
            content_str = content_str.replace("</body>", f"{script}</body>")
        elif "</html>" in content_str:
            content_str = content_str.replace("</html>", f"{script}</html>")
        else:
            content_str += script

        return content_str.encode("utf-8")
