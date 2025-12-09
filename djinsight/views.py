import json
import logging
import uuid

from django.contrib.auth.decorators import user_passes_test
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from djinsight.conf import djinsight_settings
from djinsight.models import ContentTypeRegistry
from djinsight.registry import ProviderRegistry
from djinsight.utils import get_client_ip

logger = logging.getLogger(__name__)


def validate_view_data(data):
    required_fields = ["object_id", "content_type", "url"]

    for field in required_fields:
        if not data.get(field):
            raise ValidationError(f"Field '{field}' is required")

    try:
        object_id = int(data["object_id"])
        if object_id <= 0:
            raise ValidationError("object_id must be a positive integer")
    except (ValueError, TypeError):
        raise ValidationError("object_id must be a valid integer")

    content_type = data["content_type"]
    if "." not in content_type or content_type.count(".") != 1:
        raise ValidationError("content_type must be in format 'app.Model'")

    url = data["url"]
    if len(url) > 500:
        raise ValidationError("URL is too long (max 500 characters)")

    return True


@csrf_exempt
@require_POST
@never_cache
def record_page_view(request):
    if not djinsight_settings.ENABLE_TRACKING:
        return JsonResponse({"status": "disabled"}, status=200)

    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {"status": "error", "message": "Invalid JSON"}, status=400
            )

        try:
            validate_view_data(data)
        except ValidationError as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

        object_id = int(data["object_id"])
        content_type_str = data["content_type"]
        url = data["url"]
        referrer = data.get("referrer", "")[:500]
        user_agent = data.get("user_agent", "")[:1000]

        # Check if content type is registered for tracking
        try:
            app_label, model_name = content_type_str.split(".")
            ct = ContentType.objects.get(app_label=app_label, model=model_name.lower())
            if not ContentTypeRegistry.objects.filter(
                content_type=ct, enabled=True
            ).exists():
                return JsonResponse(
                    {"status": "ignored", "message": "Content type not registered"},
                    status=200,
                )
        except (ContentType.DoesNotExist, ValueError):
            return JsonResponse(
                {"status": "ignored", "message": "Invalid content type"}, status=200
            )

        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key or str(uuid.uuid4())

        ip_address = get_client_ip(request)
        view_id = str(uuid.uuid4())
        timestamp = int(timezone.now().timestamp())

        provider = ProviderRegistry.get_provider()
        is_unique = provider.check_unique_view(session_key, content_type_str, object_id)

        event_data = {
            "view_id": view_id,
            "content_type": content_type_str,
            "object_id": object_id,
            "url": url,
            "session_key": session_key,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "referrer": referrer,
            "timestamp": timestamp,
            "is_unique": is_unique,
        }

        result = provider.record_view(event_data)

        logger.info(
            f"View recorded: object_id={object_id}, view_id={view_id}, unique={is_unique}"
        )

        return JsonResponse(result)

    except Exception as e:
        logger.error(f"Error in record_page_view: {e}")
        return JsonResponse(
            {"status": "error", "message": "Internal server error"}, status=500
        )


def check_admin_permission(user):
    if djinsight_settings.ADMIN_ONLY:
        return user.is_authenticated and user.is_staff
    return True


@user_passes_test(check_admin_permission, login_url=None)
@csrf_exempt
@require_POST
@never_cache
def get_page_stats(request):
    try:
        data = json.loads(request.body)
        page_id = data.get("page_id")
        content_type = data.get("content_type")

        if not page_id:
            return JsonResponse(
                {"status": "error", "message": "page_id required"}, status=400
            )

        try:
            page_id = int(page_id)
        except (ValueError, TypeError):
            return JsonResponse(
                {"status": "error", "message": "Invalid page_id"}, status=400
            )

        provider = ProviderRegistry.get_provider()
        stats = provider.get_stats(content_type, page_id)

        return JsonResponse(
            {
                "status": "success",
                "page_id": page_id,
                "content_type": content_type,
                **stats,
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return JsonResponse(
            {"status": "error", "message": "Internal error"}, status=500
        )
