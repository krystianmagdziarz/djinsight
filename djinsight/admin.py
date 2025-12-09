from django.contrib import admin
from django.utils.html import format_html

from djinsight.models import (
    ContentTypeRegistry,
    MCPAPIKey,
    PageViewEvent,
    PageViewStatistics,
    PageViewSummary,
)


@admin.register(ContentTypeRegistry)
class ContentTypeRegistryAdmin(admin.ModelAdmin):
    list_display = [
        "content_type",
        "enabled",
        "track_anonymous",
        "track_authenticated",
        "created_at",
    ]
    list_filter = ["enabled", "track_anonymous", "track_authenticated"]
    search_fields = ["content_type__app_label", "content_type__model"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(PageViewStatistics)
class PageViewStatisticsAdmin(admin.ModelAdmin):
    list_display = [
        "content_type",
        "object_id",
        "total_views",
        "unique_views",
        "view_ratio",
        "last_viewed_at",
    ]
    list_filter = ["content_type", "last_viewed_at"]
    search_fields = ["object_id"]
    readonly_fields = [
        "content_type",
        "object_id",
        "total_views",
        "unique_views",
        "first_viewed_at",
        "last_viewed_at",
        "updated_at",
    ]
    ordering = ["-total_views"]

    @admin.display(description="Unique Ratio")
    def view_ratio(self, obj):
        if obj.total_views > 0:
            ratio = (obj.unique_views / obj.total_views) * 100
            color = "green" if ratio > 50 else "orange" if ratio > 25 else "red"
            return format_html(
                '<span style="color: {};">{}%</span>', color, f"{ratio:.1f}"
            )
        return "-"

    def has_add_permission(self, request):
        return False


@admin.register(PageViewEvent)
class PageViewEventAdmin(admin.ModelAdmin):
    list_display = [
        "content_type",
        "object_id",
        "session_key_short",
        "timestamp",
        "is_unique",
    ]
    list_filter = ["content_type", "is_unique", "timestamp"]
    search_fields = ["object_id", "session_key", "url"]
    readonly_fields = [
        "content_type",
        "object_id",
        "url",
        "session_key",
        "ip_address",
        "user_agent",
        "referrer",
        "timestamp",
        "is_unique",
    ]
    date_hierarchy = "timestamp"
    ordering = ["-timestamp"]

    def session_key_short(self, obj):
        return f"{obj.session_key[:8]}..." if obj.session_key else "-"

    session_key_short.short_description = "Session"

    def has_add_permission(self, request):
        return False


@admin.register(PageViewSummary)
class PageViewSummaryAdmin(admin.ModelAdmin):
    list_display = [
        "content_type",
        "object_id",
        "date",
        "total_views",
        "unique_views",
        "view_ratio",
    ]
    list_filter = ["content_type", "date"]
    search_fields = ["object_id"]
    readonly_fields = [
        "content_type",
        "object_id",
        "date",
        "total_views",
        "unique_views",
    ]
    date_hierarchy = "date"
    ordering = ["-date"]

    @admin.display(description="Unique Ratio")
    def view_ratio(self, obj):
        if obj.total_views > 0:
            ratio = (obj.unique_views / obj.total_views) * 100
            color = "green" if ratio > 50 else "orange" if ratio > 25 else "red"
            return format_html(
                '<span style="color: {};">{}%</span>', color, f"{ratio:.1f}"
            )
        return "-"

    def has_add_permission(self, request):
        return False


@admin.register(MCPAPIKey)
class MCPAPIKeyAdmin(admin.ModelAdmin):
    list_display = ["name", "key_masked", "is_active", "created_at", "last_used_at"]
    list_filter = ["is_active", "created_at", "last_used_at"]
    search_fields = ["name", "description"]
    readonly_fields = ["key_display", "created_at", "last_used_at"]
    fields = [
        "name",
        "description",
        "is_active",
        "key_display",
        "created_at",
        "last_used_at",
    ]

    def key_masked(self, obj):
        if len(obj.key) > 12:
            return f"{obj.key[:8]}...{obj.key[-4:]}"
        return obj.key[:8] + "..."

    key_masked.short_description = "API Key"

    def key_display(self, obj):
        if obj.pk:
            return format_html(
                '<code style="background: #f5f5f5; padding: 8px; display: inline-block; font-size: 12px;">{}</code>',
                obj.key,
            )
        return "Will be generated on save"

    key_display.short_description = "API Key (Full)"

    def save_model(self, request, obj, form, change):
        if not change:
            obj.key = MCPAPIKey.generate_key()
        super().save_model(request, obj, form, change)
