"""Wagtail hooks for djinsight analytics integration."""

from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

from wagtail import hooks
from wagtail.admin.menu import AdminOnlyMenuItem

from djinsight.wagtail.reports import AnalyticsDashboardView


# --- Analytics URL ---

@hooks.register("register_admin_urls")
def register_analytics_urls():
    return [
        path(
            "analytics/",
            AnalyticsDashboardView.as_view(),
            name="djinsight_analytics",
        ),
    ]


# --- Main Menu Item ---

@hooks.register("register_admin_menu_item")
def register_analytics_menu_item():
    return AdminOnlyMenuItem(
        _("Analytics"),
        reverse("djinsight_analytics"),
        icon_name="view",
        order=250,
    )
