from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class PageViewStatisticsMixin(models.Model):
    """
    A mixin that adds view statistics fields to any Django model.

    Usage:
    ```python
    # For Wagtail pages
    from wagtail.models import Page
    from djinsight.models import PageViewStatisticsMixin

    class MyPage(Page, PageViewStatisticsMixin):
        pass

    # For regular Django models
    from django.db import models
    from djinsight.models import PageViewStatisticsMixin

    class Article(models.Model, PageViewStatisticsMixin):
        title = models.CharField(max_length=200)
        content = models.TextField()

        def get_absolute_url(self):
            return f'/articles/{self.pk}/'

    # For any model with URL
    class Product(models.Model, PageViewStatisticsMixin):
        name = models.CharField(max_length=100)
        price = models.DecimalField(max_digits=10, decimal_places=2)

        def get_absolute_url(self):
            return f'/products/{self.slug}/'
    ```
    """

    total_views = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Total Views"),
        help_text=_("Total number of page views"),
    )

    unique_views = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Unique Views"),
        help_text=_("Number of unique visitors"),
    )

    last_viewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Last Viewed At"),
        help_text=_("When the page was last viewed"),
    )

    first_viewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("First Viewed At"),
        help_text=_("When the page was first viewed"),
    )

    class Meta:
        abstract = True
        verbose_name = _("Page View Statistics")
        verbose_name_plural = _("Page View Statistics")

    def increment_view_count(self, unique=False):
        """
        Increment the view count for this object.

        Args:
            unique (bool): Whether this is a unique view
        """
        self.total_views += 1
        if unique:
            self.unique_views += 1

        now = timezone.now()
        self.last_viewed_at = now

        if not self.first_viewed_at:
            self.first_viewed_at = now

        self.save(
            update_fields=[
                "total_views",
                "unique_views",
                "last_viewed_at",
                "first_viewed_at",
            ]
        )

    def get_views_today(self):
        """Get number of views today"""
        from django.utils.timezone import now

        today_start = now().replace(hour=0, minute=0, second=0, microsecond=0)
        return PageViewLog.objects.filter(
            page_id=self.id, timestamp__gte=today_start
        ).count()

    def get_views_this_week(self):
        """Get number of views this week"""
        from datetime import timedelta

        from django.utils.timezone import now

        week_start = now() - timedelta(days=7)
        return PageViewLog.objects.filter(
            page_id=self.id, timestamp__gte=week_start
        ).count()

    def get_views_this_month(self):
        """Get number of views this month"""
        from django.utils.timezone import now

        month_start = now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return PageViewLog.objects.filter(
            page_id=self.id, timestamp__gte=month_start
        ).count()

    def get_content_type_label(self):
        """Get content type label for this model"""
        return self._meta.label_lower

    def get_tracking_url(self):
        """
        Get URL for tracking. Override this method if your model doesn't have get_absolute_url.

        Returns:
            str: URL to track for this object
        """
        if hasattr(self, "get_absolute_url"):
            return self.get_absolute_url()
        elif hasattr(self, "url"):
            return self.url
        else:
            # Fallback to a generic URL pattern
            return f"/{self._meta.model_name}/{self.pk}/"

    def get_display_name(self):
        """
        Get display name for this object. Override this method for custom display.

        Returns:
            str: Display name for this object
        """
        if hasattr(self, "title"):
            return self.title
        elif hasattr(self, "name"):
            return self.name
        elif hasattr(self, "__str__"):
            return str(self)
        else:
            return f"{self._meta.verbose_name} #{self.pk}"


class PageViewLog(models.Model):
    """
    A model to store detailed page view logs.
    This is used for more detailed analytics beyond the basic counters.
    Works with any model that uses PageViewStatisticsMixin.
    """

    page_id = models.PositiveIntegerField(
        verbose_name=_("Object ID"),
        help_text=_("ID of the viewed object"),
        db_index=True,
    )

    content_type = models.CharField(
        max_length=100,
        verbose_name=_("Content Type"),
        help_text=_("Content type of the viewed object"),
        db_index=True,
    )

    url = models.CharField(
        max_length=500, verbose_name=_("URL"), help_text=_("URL of the viewed object")
    )

    session_key = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("Session Key"),
        help_text=_("Session key of the visitor"),
        db_index=True,
    )

    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name=_("IP Address"),
        help_text=_("IP address of the visitor"),
    )

    user_agent = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("User Agent"),
        help_text=_("User agent of the visitor"),
    )

    referrer = models.URLField(
        blank=True,
        null=True,
        max_length=500,
        verbose_name=_("Referrer"),
        help_text=_("Referrer URL"),
    )

    timestamp = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("Timestamp"),
        help_text=_("When the object was viewed"),
        db_index=True,
    )

    is_unique = models.BooleanField(
        default=False,
        verbose_name=_("Is Unique"),
        help_text=_("Whether this is a unique view for this session"),
    )

    class Meta:
        verbose_name = _("Page View Log")
        verbose_name_plural = _("Page View Logs")
        indexes = [
            models.Index(fields=["page_id", "timestamp"]),
            models.Index(fields=["content_type", "timestamp"]),
            models.Index(fields=["session_key", "page_id"]),
            models.Index(fields=["timestamp"]),
        ]
        ordering = ["-timestamp"]

    def __str__(self):
        return f"View of {self.content_type} {self.page_id} at {self.timestamp}"


class PageViewSummary(models.Model):
    """
    A model for storing daily page view summaries for better performance.
    Works with any model that uses PageViewStatisticsMixin.
    """

    page_id = models.PositiveIntegerField(
        verbose_name=_("Object ID"),
        help_text=_("ID of the viewed object"),
        db_index=True,
    )

    content_type = models.CharField(
        max_length=100,
        verbose_name=_("Content Type"),
        help_text=_("Content type of the viewed object"),
    )

    date = models.DateField(
        verbose_name=_("Date"), help_text=_("Date of the summary"), db_index=True
    )

    total_views = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Total Views"),
        help_text=_("Total views for this day"),
    )

    unique_views = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Unique Views"),
        help_text=_("Unique views for this day"),
    )

    class Meta:
        verbose_name = _("Page View Summary")
        verbose_name_plural = _("Page View Summaries")
        unique_together = ["page_id", "date"]
        indexes = [
            models.Index(fields=["page_id", "date"]),
            models.Index(fields=["content_type", "date"]),
            models.Index(fields=["date"]),
        ]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.content_type} {self.page_id} - {self.date}: {self.total_views} views"


def has_view_statistics(obj):
    """
    Helper function to check if an object has view statistics.

    Args:
        obj: Any Django model instance

    Returns:
        bool: True if object has PageViewStatisticsMixin fields
    """
    required_fields = [
        "total_views",
        "unique_views",
        "last_viewed_at",
        "first_viewed_at",
    ]
    return all(hasattr(obj, field) for field in required_fields)
