"""Wagtail hooks for djinsight analytics integration."""

from django.conf import settings
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

from wagtail import hooks
from wagtail.admin.menu import AdminOnlyMenuItem

from djinsight.wagtail.reports import AnalyticsDashboardView

DJINSIGHT_WAGTAIL = getattr(settings, "DJINSIGHT_WAGTAIL", {})
REGISTER_ADMIN_URL = DJINSIGHT_WAGTAIL.get("REGISTER_ADMIN_URL", True)
REGISTER_MENU_ITEM = DJINSIGHT_WAGTAIL.get("REGISTER_MENU_ITEM", True)

# --- Analytics URL ---

if REGISTER_ADMIN_URL:
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

if REGISTER_MENU_ITEM:
    @hooks.register("register_admin_menu_item")
    def register_analytics_menu_item():
        return AdminOnlyMenuItem(
            _("Analytics"),
            reverse("djinsight_analytics"),
            icon_name="view",
            order=250,
        )
