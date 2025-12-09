from datetime import timedelta
from typing import Optional

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _


class ContentTypeRegistry(models.Model):
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        unique=True,
        verbose_name=_("Content Type"),
    )
    enabled = models.BooleanField(default=True, verbose_name=_("Enabled"))
    track_anonymous = models.BooleanField(default=True, verbose_name=_("Track Anonymous"))
    track_authenticated = models.BooleanField(default=True, verbose_name=_("Track Authenticated"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Content Type Registry")
        verbose_name_plural = _("Content Type Registries")
        indexes = [
            models.Index(fields=['content_type', 'enabled']),
        ]

    def __str__(self):
        return f"{self.content_type} ({'enabled' if self.enabled else 'disabled'})"

    @classmethod
    def is_tracked(cls, obj) -> bool:
        content_type = ContentType.objects.get_for_model(obj)
        registry = cls.objects.filter(content_type=content_type, enabled=True).first()
        return registry is not None

    @classmethod
    def register(cls, model_class, **kwargs):
        content_type = ContentType.objects.get_for_model(model_class)
        return cls.objects.get_or_create(content_type=content_type, defaults=kwargs)


class PageViewStatistics(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(db_index=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    total_views = models.PositiveIntegerField(default=0, verbose_name=_("Total Views"))
    unique_views = models.PositiveIntegerField(default=0, verbose_name=_("Unique Views"))
    first_viewed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("First Viewed At"))
    last_viewed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Last Viewed At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Page View Statistics")
        verbose_name_plural = _("Page View Statistics")
        unique_together = [('content_type', 'object_id')]
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['content_type', 'total_views']),
            models.Index(fields=['content_type', 'unique_views']),
            models.Index(fields=['last_viewed_at']),
            models.Index(fields=['updated_at']),
        ]

    def __str__(self):
        return f"{self.content_type} #{self.object_id}: {self.total_views} views"

    @classmethod
    def get_or_create_for_object(cls, obj):
        content_type = ContentType.objects.get_for_model(obj)
        stats, _ = cls.objects.get_or_create(
            content_type=content_type,
            object_id=obj.pk,
        )
        return stats

    @classmethod
    def get_for_object(cls, obj) -> Optional['PageViewStatistics']:
        content_type = ContentType.objects.get_for_model(obj)
        return cls.objects.filter(content_type=content_type, object_id=obj.pk).first()

    def increment_view_count(self, unique: bool = False):
        self.total_views += 1
        if unique:
            self.unique_views += 1

        current_time = timezone.now()
        self.last_viewed_at = current_time

        if not self.first_viewed_at:
            self.first_viewed_at = current_time

        self.save(update_fields=['total_views', 'unique_views', 'last_viewed_at', 'first_viewed_at', 'updated_at'])

    def get_views_for_period(self, start_date, end_date, unique: bool = False):
        queryset = PageViewEvent.objects.filter(
            content_type=self.content_type,
            object_id=self.object_id,
            timestamp__gte=start_date,
            timestamp__lte=end_date,
        )

        if unique:
            return queryset.values('session_key').distinct().count()

        return queryset.count()


class PageViewEvent(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    url = models.CharField(max_length=500, verbose_name=_("URL"))

    session_key = models.CharField(max_length=255, db_index=True, verbose_name=_("Session Key"))
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name=_("IP Address"))
    user_agent = models.TextField(blank=True, null=True, verbose_name=_("User Agent"))
    referrer = models.URLField(blank=True, null=True, max_length=500, verbose_name=_("Referrer"))

    timestamp = models.DateTimeField(default=timezone.now, db_index=True, verbose_name=_("Timestamp"))
    is_unique = models.BooleanField(default=False, verbose_name=_("Is Unique"))

    class Meta:
        verbose_name = _("Page View Event")
        verbose_name_plural = _("Page View Events")
        indexes = [
            models.Index(fields=['content_type', 'object_id', 'timestamp']),
            models.Index(fields=['session_key', 'content_type', 'object_id']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['content_type', 'timestamp']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.content_type} #{self.object_id} at {self.timestamp}"


class PageViewSummary(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    date = models.DateField(db_index=True, verbose_name=_("Date"))

    total_views = models.PositiveIntegerField(default=0, verbose_name=_("Total Views"))
    unique_views = models.PositiveIntegerField(default=0, verbose_name=_("Unique Views"))

    class Meta:
        verbose_name = _("Page View Summary")
        verbose_name_plural = _("Page View Summaries")
        unique_together = [('content_type', 'object_id', 'date')]
        indexes = [
            models.Index(fields=['content_type', 'object_id', 'date']),
            models.Index(fields=['content_type', 'date']),
            models.Index(fields=['date']),
        ]
        ordering = ['-date']

    def __str__(self):
        return f"{self.content_type} #{self.object_id} - {self.date}: {self.total_views} views"


class StatsQueryMixin:

    @classmethod
    def get_stats_for_object(cls, obj):
        return PageViewStatistics.get_for_object(obj)

    @classmethod
    def get_views_today(cls, obj, chart_data: bool = False):
        stats = cls.get_stats_for_object(obj)
        if not stats:
            return [] if chart_data else 0

        today_start = now().replace(hour=0, minute=0, second=0, microsecond=0)
        content_type = ContentType.objects.get_for_model(obj)

        if chart_data:
            data = []
            for hour in range(24):
                hour_start = today_start.replace(hour=hour)
                hour_end = hour_start + timedelta(hours=1)

                if hour_end > now():
                    break

                count = PageViewEvent.objects.filter(
                    content_type=content_type,
                    object_id=obj.pk,
                    timestamp__gte=hour_start,
                    timestamp__lt=hour_end,
                ).count()

                data.append({
                    'date': hour_start.strftime('%Y-%m-%d %H:00'),
                    'label': f"{hour:02d}:00",
                    'count': count,
                })
            return data

        return PageViewEvent.objects.filter(
            content_type=content_type,
            object_id=obj.pk,
            timestamp__gte=today_start,
        ).count()

    @classmethod
    def get_views_period(cls, obj, days: int, chart_data: bool = False):
        stats = cls.get_stats_for_object(obj)
        if not stats:
            return [] if chart_data else 0

        start_date = now() - timedelta(days=days - 1)
        content_type = ContentType.objects.get_for_model(obj)

        if chart_data:
            data = []
            current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

            for i in range(days):
                day = current_date + timedelta(days=i)
                day_end = day + timedelta(days=1)

                summary = PageViewSummary.objects.filter(
                    content_type=content_type,
                    object_id=obj.pk,
                    date=day.date(),
                ).first()

                count = summary.total_views if summary else PageViewEvent.objects.filter(
                    content_type=content_type,
                    object_id=obj.pk,
                    timestamp__gte=day,
                    timestamp__lt=day_end,
                ).count()

                data.append({
                    'date': day.strftime('%Y-%m-%d'),
                    'label': day.strftime('%a' if days <= 7 else '%d %b'),
                    'count': count,
                })
            return data

        return PageViewEvent.objects.filter(
            content_type=content_type,
            object_id=obj.pk,
            timestamp__gte=start_date,
        ).count()

    @classmethod
    def get_views_week(cls, obj, chart_data: bool = False):
        return cls.get_views_period(obj, 7, chart_data)

    @classmethod
    def get_views_month(cls, obj, chart_data: bool = False):
        return cls.get_views_period(obj, 30, chart_data)

    @classmethod
    def get_views_year(cls, obj, chart_data: bool = False):
        stats = cls.get_stats_for_object(obj)
        if not stats:
            return [] if chart_data else 0

        year_start = now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        content_type = ContentType.objects.get_for_model(obj)

        if chart_data:
            data = []
            for i in range(11, -1, -1):
                month_date = now().replace(day=1) - timedelta(days=i * 30)
                month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

                if month_start.month == 12:
                    month_end = month_start.replace(year=month_start.year + 1, month=1)
                else:
                    month_end = month_start.replace(month=month_start.month + 1)

                summaries = PageViewSummary.objects.filter(
                    content_type=content_type,
                    object_id=obj.pk,
                    date__gte=month_start.date(),
                    date__lt=month_end.date(),
                ).aggregate(total=Sum('total_views'))

                count = summaries['total'] or PageViewEvent.objects.filter(
                    content_type=content_type,
                    object_id=obj.pk,
                    timestamp__gte=month_start,
                    timestamp__lt=month_end,
                ).count()

                data.append({
                    'date': month_start.strftime('%Y-%m'),
                    'label': month_start.strftime('%b %Y'),
                    'count': count,
                })
            return data

        return PageViewEvent.objects.filter(
            content_type=content_type,
            object_id=obj.pk,
            timestamp__gte=year_start,
        ).count()

    @classmethod
    def get_unique_views_period(cls, obj, start_date, end_date=None):
        if not end_date:
            end_date = now()

        content_type = ContentType.objects.get_for_model(obj)
        return PageViewEvent.objects.filter(
            content_type=content_type,
            object_id=obj.pk,
            timestamp__gte=start_date,
            timestamp__lte=end_date,
        ).values('session_key').distinct().count()


def get_stats_for_object(obj):
    return PageViewStatistics.get_for_object(obj)


class MCPAPIKey(models.Model):
    key = models.CharField(max_length=64, unique=True, verbose_name=_("API Key"))
    name = models.CharField(max_length=200, verbose_name=_("Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Last Used At"))

    class Meta:
        verbose_name = _("MCP API Key")
        verbose_name_plural = _("MCP API Keys")
        indexes = [
            models.Index(fields=['key', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({'active' if self.is_active else 'inactive'})"

    @classmethod
    def generate_key(cls):
        import secrets
        return secrets.token_urlsafe(48)

    @classmethod
    def create_key(cls, name, description=""):
        key = cls.generate_key()
        return cls.objects.create(
            key=key,
            name=name,
            description=description,
        )

    @classmethod
    def validate_key(cls, key):
        try:
            api_key = cls.objects.get(key=key, is_active=True)
            api_key.last_used_at = timezone.now()
            api_key.save(update_fields=['last_used_at'])
            return True
        except cls.DoesNotExist:
            return False
