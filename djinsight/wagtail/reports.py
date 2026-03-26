"""Analytics report views for Wagtail admin."""

from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from wagtail.admin.views.reports import ReportView

from djinsight.mcp.tools.behavior import get_device_breakdown
from djinsight.mcp.tools.referrers import get_traffic_sources
from djinsight.models import PageViewEvent, PageViewStatistics


class PageViewsReportView(ReportView):
    """Full page views report with sorting, filtering, and CSV/XLSX export."""

    page_title = _("Page Views")
    header_icon = "doc-empty"
    index_url_name = "djinsight_page_views_report"
    index_results_url_name = "djinsight_page_views_report_results"

    list_export = [
        "title",
        "content_type",
        "total_views",
        "unique_views",
        "last_viewed_at",
    ]
    export_headings = {
        "title": _("Title"),
        "content_type": _("Content Type"),
        "total_views": _("Total Views"),
        "unique_views": _("Unique Views"),
        "last_viewed_at": _("Last Viewed"),
    }

    template_name = "djinsight/wagtail/reports/page_views.html"
    results_template_name = "djinsight/wagtail/reports/page_views_results.html"

    def get_queryset(self):
        qs = (
            PageViewStatistics.objects.select_related("content_type")
            .order_by("-total_views")
        )

        # Period filtering
        period = self.request.GET.get("period", "all")
        if period != "all":
            period_map = {
                "today": timedelta(days=1),
                "week": timedelta(days=7),
                "month": timedelta(days=30),
                "year": timedelta(days=365),
            }
            delta = period_map.get(period)
            if delta:
                cutoff = timezone.now() - delta
                qs = qs.filter(last_viewed_at__gte=cutoff)

        # Content type filtering
        ct_filter = self.request.GET.get("content_type")
        if ct_filter:
            try:
                app_label, model = ct_filter.split(".")
                ct = ContentType.objects.get_by_natural_key(app_label, model)
                qs = qs.filter(content_type=ct)
            except (ValueError, ContentType.DoesNotExist):
                pass

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Aggregate stats
        qs = self.get_queryset()
        aggregates = qs.aggregate(
            total_views=Sum("total_views"),
            total_unique=Sum("unique_views"),
        )
        context["total_views"] = aggregates["total_views"] or 0
        context["total_unique"] = aggregates["total_unique"] or 0
        context["total_objects"] = qs.count()

        # Available content types for filter dropdown
        tracked_cts = (
            PageViewStatistics.objects.values(
                "content_type__app_label", "content_type__model"
            )
            .distinct()
            .order_by("content_type__app_label", "content_type__model")
        )
        context["content_types"] = [
            f"{row['content_type__app_label']}.{row['content_type__model']}"
            for row in tracked_cts
        ]

        context["current_period"] = self.request.GET.get("period", "all")
        context["current_content_type"] = self.request.GET.get("content_type", "")

        # Hydrate results with object titles
        context["results_data"] = self._hydrate_results(context["object_list"])
        return context

    def _hydrate_results(self, stats_qs):
        """Add object titles and edit URLs to stats queryset."""
        results = []
        for stat in stats_qs:
            ct = stat.content_type
            model_class = ct.model_class()
            title = f"{ct.app_label}.{ct.model} #{stat.object_id}"
            edit_url = None
            obj_type = f"{ct.app_label}.{ct.model}"

            if model_class:
                try:
                    obj = model_class.objects.get(pk=stat.object_id)
                    title = str(obj)
                    if hasattr(obj, "id"):
                        try:
                            from wagtail.admin.urls import get_edit_url
                            edit_url = get_edit_url(obj)
                        except Exception:
                            pass
                except model_class.DoesNotExist:
                    title += " (deleted)"

            results.append({
                "title": title,
                "content_type": obj_type,
                "total_views": stat.total_views,
                "unique_views": stat.unique_views,
                "last_viewed_at": stat.last_viewed_at,
                "edit_url": edit_url,
                "stat": stat,
            })
        return results


class TrafficSourcesReportView(ReportView):
    """Traffic sources breakdown report."""

    page_title = _("Traffic Sources")
    header_icon = "globe"
    index_url_name = "djinsight_traffic_sources_report"
    index_results_url_name = "djinsight_traffic_sources_report_results"
    template_name = "djinsight/wagtail/reports/traffic_sources.html"

    def get_queryset(self):
        return PageViewEvent.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        period = self.request.GET.get("period", "month")

        # Get all tracked content types
        tracked_cts = (
            PageViewStatistics.objects.values(
                "content_type__app_label", "content_type__model"
            ).distinct()
        )

        # Aggregate traffic sources across all content types
        source_totals = {"direct": 0, "search": 0, "social": 0, "referral": 0}
        for row in tracked_cts:
            ct_str = f"{row['content_type__app_label']}.{row['content_type__model']}"
            result = get_traffic_sources(ct_str, period=period)
            if "error" not in result:
                for source in result.get("sources", []):
                    name = source["source"]
                    if name in source_totals:
                        source_totals[name] += source["views"]

        total = sum(source_totals.values())
        sources = []
        for name, views in sorted(source_totals.items(), key=lambda x: -x[1]):
            sources.append({
                "source": name,
                "views": views,
                "percentage": round(views / total * 100, 1) if total else 0,
            })

        context["sources"] = sources
        context["total_views"] = total
        context["current_period"] = period

        # Device breakdown
        device_totals = {}
        for row in tracked_cts:
            ct_str = f"{row['content_type__app_label']}.{row['content_type__model']}"
            result = get_device_breakdown(ct_str, period=period)
            if "error" not in result:
                for device in result.get("devices", []):
                    name = device["device"]
                    device_totals[name] = device_totals.get(name, 0) + device["views"]

        device_total = sum(device_totals.values())
        devices = []
        for name, views in sorted(device_totals.items(), key=lambda x: -x[1]):
            devices.append({
                "device": name,
                "views": views,
                "percentage": round(views / device_total * 100, 1) if device_total else 0,
            })

        context["devices"] = devices
        context["device_total"] = device_total

        return context
