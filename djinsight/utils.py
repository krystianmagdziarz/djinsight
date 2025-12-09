def get_client_ip(request) -> str:
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def parse_user_agent(user_agent: str) -> dict:
    return {"raw": user_agent}


def get_object_url(obj, request=None) -> str:
    if hasattr(obj, "get_tracking_url"):
        return obj.get_tracking_url()
    if hasattr(obj, "get_absolute_url"):
        return obj.get_absolute_url()
    if hasattr(obj, "url"):
        return obj.url
    return request.path if request else "/"


def get_content_type_label(obj) -> str:
    if hasattr(obj, "get_content_type_label"):
        return obj.get_content_type_label()
    return obj._meta.label_lower


def get_object_from_context(context, obj=None):
    """Get object from context for tracking/stats. Returns object if it has pk."""
    if obj and hasattr(obj, "pk") and obj.pk:
        return obj

    if obj is None:
        for var_name in ["page", "object", "article", "post", "item", "product"]:
            potential_obj = context.get(var_name)
            if potential_obj and hasattr(potential_obj, "pk") and potential_obj.pk:
                return potential_obj

    return None


def format_view_count(count) -> str:
    try:
        count = int(count)
    except (ValueError, TypeError):
        return str(count)

    if count < 1000:
        return str(count)
    elif count < 1000000:
        return f"{count / 1000:.1f}K"
    else:
        return f"{count / 1000000:.1f}M"


def check_stats_permission(request) -> bool:
    from djinsight.conf import djinsight_settings

    if djinsight_settings.ADMIN_ONLY and request:
        user = getattr(request, "user", None)
        if user:
            return user.is_authenticated and user.is_staff
        return False
    return True
