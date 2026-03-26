"""Homepage dashboard panels for Wagtail admin."""

from django.db.models import Sum
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from wagtail.admin.site_summary import SummaryItem
from wagtail.admin.ui.components import Component

from djinsight.models import PageViewEvent, PageViewStatistics


class TotalViewsSummaryItem(SummaryItem):
    """Summary bar item showing total page views."""

    order = 200
    template_name = "djinsight/wagtail/panels/summary_item.html"

    def get_context_data(self, parent_context):
        total = PageViewStatistics.objects.aggregate(
            total=Sum("total_views")
        )["total"] or 0
        return {
            "total_views": total,
            "label": _("Total views"),
        }


class UniqueViewsSummaryItem(SummaryItem):
    """Summary bar item showing unique page views."""

    order = 201
    template_name = "djinsight/wagtail/panels/summary_item.html"

    def get_context_data(self, parent_context):
        total = PageViewStatistics.objects.aggregate(
            total=Sum("unique_views")
        )["total"] or 0
        return {
            "total_views": total,
            "label": _("Unique views"),
        }


class AnalyticsPanel(Component):
    """Homepage panel showing top pages and a 7-day trend mini chart."""

    order = 110
    template_name = "djinsight/wagtail/panels/analytics_panel.html"

    def get_context_data(self, parent_context):
        from datetime import timedelta

        from django.contrib.contenttypes.models import ContentType
        from django.db.models.functions import TruncDate

        now = timezone.now()
        week_ago = now - timedelta(days=7)

        # Top 5 pages by views
        top_pages = list(
            PageViewStatistics.objects.select_related("content_type")
            .order_by("-total_views")[:5]
        )

        top_pages_data = []
        for stat in top_pages:
            ct = stat.content_type
            model_class = ct.model_class()
            title = f"{ct.app_label}.{ct.model} #{stat.object_id}"
            edit_url = None

            if model_class:
                try:
                    obj = model_class.objects.get(pk=stat.object_id)
                    title = str(obj)
                    # Try to get Wagtail edit URL for pages
                    if hasattr(obj, "get_url"):
                        from wagtail.admin.urls import get_edit_url
                        edit_url = get_edit_url(obj)
                except (model_class.DoesNotExist, Exception):
                    pass

            top_pages_data.append({
                "title": title,
                "total_views": stat.total_views,
                "unique_views": stat.unique_views,
                "edit_url": edit_url,
            })

        # 7-day trend data for mini chart
        daily_views = (
            PageViewEvent.objects.filter(timestamp__gte=week_ago)
            .annotate(day=TruncDate("timestamp"))
            .values("day")
            .annotate(views=Sum("id"))  # Count via annotation
            .order_by("day")
        )

        # Build complete 7-day series (fill gaps with 0)
        from django.db.models import Count

        daily_views = (
            PageViewEvent.objects.filter(timestamp__gte=week_ago)
            .annotate(day=TruncDate("timestamp"))
            .values("day")
            .annotate(views=Count("id"))
            .order_by("day")
        )
        views_by_day = {entry["day"]: entry["views"] for entry in daily_views}

        chart_labels = []
        chart_data = []
        for i in range(7):
            day = (week_ago + timedelta(days=i)).date()
            chart_labels.append(day.strftime("%a"))
            chart_data.append(views_by_day.get(day, 0))

        return {
            "top_pages": top_pages_data,
            "chart_labels": chart_labels,
            "chart_data": chart_data,
            "total_week_views": sum(chart_data),
        }
