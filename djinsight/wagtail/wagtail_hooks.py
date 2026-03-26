"""Wagtail hooks for djinsight analytics integration."""

from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

from wagtail import hooks
from wagtail.admin.menu import AdminOnlyMenuItem

from djinsight.wagtail.panels import (
    AnalyticsPanel,
    TotalViewsSummaryItem,
    UniqueViewsSummaryItem,
)
from djinsight.wagtail.reports import PageViewsReportView, TrafficSourcesReportView


# --- Homepage Summary Items ---

@hooks.register("construct_homepage_summary_items")
def add_analytics_summary_items(request, items):
    items.append(TotalViewsSummaryItem(request))
    items.append(UniqueViewsSummaryItem(request))


# --- Homepage Panel ---

@hooks.register("construct_homepage_panels")
def add_analytics_panel(request, panels):
    panels.append(AnalyticsPanel())


# --- Report URLs ---

@hooks.register("register_admin_urls")
def register_report_urls():
    return [
        path(
            "reports/page-views/",
            PageViewsReportView.as_view(),
            name="djinsight_page_views_report",
        ),
        path(
            "reports/page-views/results/",
            PageViewsReportView.as_view(results_only=True),
            name="djinsight_page_views_report_results",
        ),
        path(
            "reports/traffic-sources/",
            TrafficSourcesReportView.as_view(),
            name="djinsight_traffic_sources_report",
        ),
        path(
            "reports/traffic-sources/results/",
            TrafficSourcesReportView.as_view(results_only=True),
            name="djinsight_traffic_sources_report_results",
        ),
    ]


# --- Reports Menu Items ---

@hooks.register("register_reports_menu_item")
def register_page_views_report():
    return AdminOnlyMenuItem(
        _("Page Views"),
        reverse("djinsight_page_views_report"),
        icon_name="doc-empty",
        order=700,
    )


@hooks.register("register_reports_menu_item")
def register_traffic_sources_report():
    return AdminOnlyMenuItem(
        _("Traffic Sources"),
        reverse("djinsight_traffic_sources_report"),
        icon_name="globe",
        order=710,
    )
