import json

from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from djinsight.conf import djinsight_settings
from djinsight.utils import (
    check_stats_permission,
    format_view_count,
    get_object_from_context,
)

register = template.Library()


@register.simple_tag(takes_context=True)
def stats(
    context,
    metric="views",
    period="total",
    output="text",
    obj=None,
    chart_type="line",
    chart_color=None,
    start_date=None,
    end_date=None,
    **kwargs,
):
    request = context.get("request")
    if not check_stats_permission(request):
        return ""

    obj = get_object_from_context(context, obj)
    if not obj:
        return ""

    renderer_class = djinsight_settings.get_widget_renderer()
    renderer = renderer_class(
        obj=obj,
        metric=metric,
        period=period,
        output=output,
        chart_type=chart_type,
        chart_color=chart_color,
        start_date=start_date,
        end_date=end_date,
        context=context,
        **kwargs,
    )

    return mark_safe(renderer.render())


@register.filter
def format_count(count):
    return format_view_count(count)


@register.filter
def to_json(data):
    return mark_safe(json.dumps(data))


@register.simple_tag(takes_context=True)
def track(context, obj=None):
    from django.urls import NoReverseMatch, reverse

    from djinsight.utils import get_content_type_label, get_object_url

    request = context.get("request")
    if not request or not djinsight_settings.ENABLE_TRACKING:
        return ""

    obj = get_object_from_context(context, obj)
    if not obj:
        return ""

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

    return mark_safe(
        render_to_string(
            "djinsight/tracking_script.html",
            {
                "object_data": object_data,
                "record_url": record_url,
                "async_load": True,
                "debug": False,
            },
        )
    )
