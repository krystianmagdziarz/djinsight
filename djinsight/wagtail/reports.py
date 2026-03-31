"""Analytics dashboard view for Wagtail admin."""

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from django import forms
from django.contrib.auth.views import redirect_to_login
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from wagtail.admin.admin_url_finder import AdminURLFinder
from wagtail.admin.views.generic.base import WagtailAdminTemplateMixin
from wagtail.admin.widgets.datetime import AdminDateInput

from djinsight.models import PageViewEvent, PageViewStatistics


class AnalyticsFilterForm(forms.Form):
    """Filter form with Wagtail date picker widgets."""

    period = forms.ChoiceField(
        choices=[
            ("all", _("All time")),
            ("today", _("Today")),
            ("week", _("This week")),
            ("month", _("This month")),
            ("year", _("This year")),
        ],
        required=False,
        initial="all",
    )
    date_from = forms.DateField(
        required=False,
        widget=AdminDateInput(attrs={"placeholder": _("From")}),
        label=_("From"),
    )
    date_to = forms.DateField(
        required=False,
        widget=AdminDateInput(attrs={"placeholder": _("To")}),
        label=_("To"),
    )
    content_type = forms.ChoiceField(
        required=False,
        label=_("Content type"),
    )

    def __init__(self, *args, content_type_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        ct_choices = [("", _("All"))]
        if content_type_choices:
            ct_choices += [(ct, ct) for ct in content_type_choices]
        self.fields["content_type"].choices = ct_choices

PAGE_SIZE = 25

PERIOD_PRESETS = {
    "today": timedelta(days=1),
    "week": timedelta(days=7),
    "month": timedelta(days=30),
    "year": timedelta(days=365),
}


class AnalyticsDashboardView(WagtailAdminTemplateMixin, TemplateView):
    """Combined analytics dashboard: page views + traffic sources + devices."""

    page_title = _("Analytics")
    header_icon = "view"
    template_name = "djinsight/wagtail/reports/analytics_dashboard.html"

    def get_breadcrumbs_items(self):
        return self.breadcrumbs_items + [
            {"url": "", "label": _("Analytics")},
        ]

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return redirect_to_login(request.get_full_path())
        return super().dispatch(request, *args, **kwargs)

    def _get_date_range(self):
        """Parse date range from request: preset or custom date_from/date_to."""
        period = self.request.GET.get("period", "all")
        date_from = self.request.GET.get("date_from", "")
        date_to = self.request.GET.get("date_to", "")

        now = timezone.now()

        # Custom date range takes priority
        if date_from or date_to:
            start = None
            end = None
            if date_from:
                try:
                    start = timezone.make_aware(datetime.strptime(date_from, "%Y-%m-%d"))
                except ValueError:
                    pass
            if date_to:
                try:
                    end = timezone.make_aware(
                        datetime.strptime(date_to, "%Y-%m-%d").replace(
                            hour=23, minute=59, second=59
                        )
                    )
                except ValueError:
                    pass
            return start, end, "custom"

        if period != "all" and period in PERIOD_PRESETS:
            return now - PERIOD_PRESETS[period], now, period

        return None, None, "all"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Available content types for filter
        tracked_cts = (
            PageViewStatistics.objects.values("content_type__app_label", "content_type__model")
            .distinct()
            .order_by("content_type__app_label", "content_type__model")
        )
        ct_choices = [
            f"{row['content_type__app_label']}.{row['content_type__model']}"
            for row in tracked_cts
        ]

        # Filter form with Wagtail date pickers
        form = AnalyticsFilterForm(
            self.request.GET or None,
            content_type_choices=ct_choices,
        )
        context["filter_form"] = form

        date_from, date_to, period = self._get_date_range()
        ct_filter = self.request.GET.get("content_type", "")

        # --- Page Views table ---
        qs = PageViewStatistics.objects.select_related("content_type").order_by("-total_views")

        if date_from:
            qs = qs.filter(last_viewed_at__gte=date_from)
        if date_to:
            qs = qs.filter(last_viewed_at__lte=date_to)

        if ct_filter:
            try:
                app_label, model = ct_filter.split(".")
                ct = ContentType.objects.get_by_natural_key(app_label, model)
                qs = qs.filter(content_type=ct)
            except (ValueError, ContentType.DoesNotExist):
                pass

        aggregates = qs.aggregate(
            total_views=Sum("total_views"),
            total_unique=Sum("unique_views"),
        )
        context["total_views"] = aggregates["total_views"] or 0
        context["total_unique"] = aggregates["total_unique"] or 0
        context["total_objects"] = qs.count()

        # Pagination
        paginator = Paginator(qs, PAGE_SIZE)
        page_number = self.request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)
        context["results_data"] = self._hydrate_results(page_obj)
        context["page_obj"] = page_obj
        context["paginator"] = paginator

        context["current_period"] = period

        # --- Event filters (shared by chart, traffic sources, devices) ---
        event_filters = {}
        if date_from:
            event_filters["timestamp__gte"] = date_from
        if date_to:
            event_filters["timestamp__lte"] = date_to
        if ct_filter:
            try:
                app_label, model = ct_filter.split(".")
                ct = ContentType.objects.get_by_natural_key(app_label, model)
                event_filters["content_type"] = ct
            except (ValueError, ContentType.DoesNotExist):
                pass

        # --- Daily chart data (views + unique) ---
        daily_events = (
            PageViewEvent.objects.filter(**event_filters)
            .annotate(day=TruncDate("timestamp"))
            .values("day")
            .annotate(
                total=Count("id"),
                unique=Count("session_key", distinct=True),
            )
            .order_by("day")
        )
        views_by_day = {entry["day"]: entry for entry in daily_events}

        # Build complete series filling gaps with 0

        if date_from and date_to:
            start_date = date_from.date() if hasattr(date_from, "date") else date_from
            end_date = date_to.date() if hasattr(date_to, "date") else date_to
        elif date_from:
            start_date = date_from.date() if hasattr(date_from, "date") else date_from
            end_date = timezone.now().date()
        elif views_by_day:
            start_date = min(views_by_day.keys())
            end_date = max(views_by_day.keys())
        else:
            start_date = (timezone.now() - timedelta(days=30)).date()
            end_date = timezone.now().date()

        chart_labels = []
        chart_views = []
        chart_unique = []
        current = start_date
        while current <= end_date:
            chart_labels.append(current.strftime("%Y-%m-%d"))
            entry = views_by_day.get(current, {})
            chart_views.append(entry.get("total", 0))
            chart_unique.append(entry.get("unique", 0))
            current += timedelta(days=1)

        context["chart_labels_json"] = json.dumps(chart_labels)
        context["chart_views_json"] = json.dumps(chart_views)
        context["chart_unique_json"] = json.dumps(chart_unique)

        # Build query string for pagination links (without page param)
        qs_params = self.request.GET.copy()
        qs_params.pop("page", None)
        context["pagination_qs"] = qs_params.urlencode()

        # --- Traffic Sources & Devices ---
        events = PageViewEvent.objects.filter(**event_filters)

        # Traffic sources
        source_counter = Counter()
        for referrer in events.values_list("referrer", flat=True).iterator():
            source_counter[self._classify_referrer(referrer)] += 1

        source_total = sum(source_counter.values())
        context["sources"] = [
            {
                "source": name,
                "views": views,
                "percentage": round(views / source_total * 100, 1) if source_total else 0,
            }
            for name, views in source_counter.most_common()
        ]
        context["source_total"] = source_total

        # Device breakdown
        device_counter = Counter()
        for ua in events.values_list("user_agent", flat=True).iterator():
            device_counter[self._classify_device(ua)] += 1

        device_total = sum(device_counter.values())
        context["devices"] = [
            {
                "device": name,
                "views": views,
                "percentage": round(views / device_total * 100, 1) if device_total else 0,
            }
            for name, views in device_counter.most_common()
        ]
        context["device_total"] = device_total

        return context

    def _hydrate_results(self, stats_qs):
        stats_list = list(stats_qs)
        if not stats_list:
            return []
        results = []
        url_finder = AdminURLFinder()
        by_ct = defaultdict(list)
        for stat in stats_list:
            by_ct[stat.content_type_id].append(stat)
        objects_cache = {}
        for ct_id, ct_stats in by_ct.items():
            ct = ct_stats[0].content_type
            model_class = ct.model_class()
            if model_class:
                obj_ids = [s.object_id for s in ct_stats]
                for obj in model_class.objects.filter(pk__in=obj_ids):
                    objects_cache[(ct_id, obj.pk)] = obj
                    
        for stat in stats_list:
            ct = stat.content_type
            title = f"{ct.app_label}.{ct.model} #{stat.object_id}"
            edit_url = None
            
            obj = objects_cache.get((stat.content_type_id, stat.object_id))
            
            if obj:
                title = str(obj)
                edit_url = url_finder.get_edit_url(obj)
            elif ct.model_class():
                title += " (deleted)"
            results.append({
                "title": title,
                "content_type": f"{ct.app_label}.{ct.model}",
                "total_views": stat.total_views,
                "unique_views": stat.unique_views,
                "last_viewed_at": stat.last_viewed_at,
                "edit_url": edit_url,
            }) 
        return results

    @staticmethod
    def _classify_referrer(referrer):
        if not referrer:
            return "direct"
        referrer = referrer.lower()
        search = ["google.", "bing.", "yahoo.", "duckduckgo.", "baidu.", "yandex."]
        social = ["facebook.", "twitter.", "t.co", "instagram.", "linkedin.", "reddit.", "youtube."]
        if any(s in referrer for s in search):
            return "search"
        if any(s in referrer for s in social):
            return "social"
        return "referral"

    @staticmethod
    def _classify_device(user_agent):
        if not user_agent:
            return "unknown"
        ua = user_agent.lower()
        if any(bot in ua for bot in ["bot", "spider", "crawler", "slurp"]):
            return "bot"
        if any(m in ua for m in ["iphone", "android", "mobile"]):
            return "mobile"
        if any(t in ua for t in ["ipad", "tablet"]):
            return "tablet"
        return "desktop"
