# Migration Guide: djinsight v0.1.x → v0.2.0

## Overview

Version 0.2.0 is a **major rewrite** with significant architectural improvements:

- ✅ No more mixins - statistics stored in separate tables
- ✅ ContentType-based tracking - track any model without modifying it
- ✅ One universal `{% stats %}` tag instead of 20+ redundant tags
- ✅ Automatic middleware-based tracking injection
- ✅ Fully extensible architecture via settings
- ✅ MCP-style provider system for custom backends

## Breaking Changes

### 1. Model Changes

**OLD (v0.1.x):**
```python
from djinsight.models import PageViewStatisticsMixin

class Article(models.Model, PageViewStatisticsMixin):
    title = models.CharField(max_length=200)
    # Mixin added fields: total_views, unique_views, etc.
```

**NEW (v0.2.0):**
```python
# NO MIXIN NEEDED! Clean models
class Article(models.Model):
    title = models.CharField(max_length=200)

# Register for tracking in your AppConfig:
from django.apps import AppConfig
from djinsight.models import ContentTypeRegistry

class BlogConfig(AppConfig):
    def ready(self):
        from blog.models import Article
        ContentTypeRegistry.register(Article)
```

### 2. Template Tag Changes

**OLD (v0.1.x):**
```django
{% load djinsight_tags %}

{% total_views_stat %}
{% unique_views_stat %}
{% views_today_stat %}
{% views_week_stat show_chart=True %}
{% views_month_stat show_chart=True chart_type="line" %}
{% unique_views_year_stat %}
{% page_view_tracker %}  {# Manual tracking script #}
```

**NEW (v0.2.0):**
```django
{% load djinsight_tags %}

{# ONE universal tag for everything! #}
{% stats metric="views" period="today" output="text" %}
{% stats metric="unique_views" period="week" output="chart" chart_type="line" %}
{% stats metric="views" period="month" output="widget" %}
{% stats metric="all" period="year" output="json" %}

{# Optional: Manual tracking (auto-injected by middleware) #}
{% track %}
```

### 3. Middleware (New!)

**Add to settings.py:**
```python
MIDDLEWARE = [
    # ... other middleware
    'djinsight.middleware.TrackingMiddleware',  # NEW!
]

DJINSIGHT = {
    'AUTO_INJECT_TRACKING': True,  # Automatic JS injection
    'ENABLE_TRACKING': True,
}
```

### 4. Settings Structure

**OLD (v0.1.x):**
```python
DJINSIGHT_ENABLE_TRACKING = True
DJINSIGHT_ADMIN_ONLY = False
DJINSIGHT_REDIS_HOST = 'localhost'
# ... many separate settings
```

**NEW (v0.2.0):**
```python
DJINSIGHT = {
    # Core settings
    'ENABLE_TRACKING': True,
    'AUTO_INJECT_TRACKING': True,
    'ADMIN_ONLY': False,

    # Redis settings
    'REDIS_HOST': 'localhost',
    'REDIS_PORT': 6379,
    'REDIS_DB': 0,
    'REDIS_PASSWORD': None,

    # Extensibility - provide your own implementations!
    'MIDDLEWARE_CLASS': 'djinsight.middleware.TrackingMiddleware',
    'WIDGET_RENDERER': 'djinsight.renderers.DefaultWidgetRenderer',
    'CHART_RENDERER': 'djinsight.renderers.DefaultChartRenderer',
    'PROVIDER_CLASS': 'djinsight.providers.redis.RedisProvider',

    # Tracking preferences
    'TRACK_ANONYMOUS': True,
    'TRACK_AUTHENTICATED': True,
    'TRACK_STAFF': True,

    # Data retention
    'RETENTION_DAYS': 365,
    'SUMMARY_RETENTION_DAYS': 730,
}
```

## Migration Steps

### Step 1: Backup Your Database

```bash
python manage.py dumpdata djinsight > djinsight_backup.json
```

### Step 2: Install djinsight v0.2.0

```bash
pip install djinsight==0.2.0
```

### Step 3: Run New Migrations

```bash
python manage.py migrate djinsight
```

This creates new tables:
- `djinsight_contenttyperegistry`
- `djinsight_pageviewstatistics` (replaces mixin fields)
- `djinsight_pageviewevent` (replaces PageViewLog)
- `djinsight_pageviewsummary` (enhanced version)

### Step 4: Migrate Existing Data

```bash
# Dry run first (no changes)
python manage.py migrate_to_v2 --dry-run

# Actual migration
python manage.py migrate_to_v2

# With custom batch size
python manage.py migrate_to_v2 --batch-size=500
```

This migrates:
- All PageViewLog → PageViewEvent
- All PageViewSummary → new format with ContentType
- All mixin statistics → PageViewStatistics table
- Auto-registers tracked models in ContentTypeRegistry

### Step 5: Update Your Code

#### Update Models
Remove `PageViewStatisticsMixin` from your models:

```python
# OLD
class Article(models.Model, PageViewStatisticsMixin):
    title = models.CharField(max_length=200)

# NEW - clean!
class Article(models.Model):
    title = models.CharField(max_length=200)
```

#### Register Models for Tracking

```python
# blog/apps.py
from django.apps import AppConfig

class BlogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'blog'

    def ready(self):
        from djinsight.models import ContentTypeRegistry
        from blog.models import Article, Post

        ContentTypeRegistry.register(Article)
        ContentTypeRegistry.register(Post)
```

#### Update Templates

Replace old tags with universal `{% stats %}`:

```django
{# OLD #}
{% views_week_stat show_chart=True chart_type="line" chart_color="#007bff" %}

{# NEW #}
{% stats metric="views" period="week" output="chart" chart_type="line" chart_color="#007bff" %}
```

#### Add Middleware

```python
# settings.py
MIDDLEWARE = [
    # ...
    'djinsight.middleware.TrackingMiddleware',
]
```

#### Update Settings

**Option 1: Synchronous (no Redis/Celery):**
```python
DJINSIGHT = {
    'ENABLE_TRACKING': True,
    'AUTO_INJECT_TRACKING': True,
    'USE_REDIS': False,  # Direct database writes
    'USE_CELERY': False,
}
```

**Option 2: Async with Redis + Celery:**
```python
DJINSIGHT = {
    'ENABLE_TRACKING': True,
    'AUTO_INJECT_TRACKING': True,
    'USE_REDIS': True,
    'USE_CELERY': True,
    'REDIS_HOST': 'localhost',
    'REDIS_PORT': 6379,
}
```

### Step 6: Create Migration for Removing Mixin Fields (Optional)

Once you've verified everything works, you can remove the old mixin fields:

```bash
# This will create a migration to remove old fields
python manage.py makemigrations blog --name remove_pageview_mixin_fields
python manage.py migrate
```

Or manually create a migration:

```python
# blog/migrations/XXXX_remove_mixin_fields.py
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('blog', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(model_name='article', name='total_views'),
        migrations.RemoveField(model_name='article', name='unique_views'),
        migrations.RemoveField(model_name='article', name='first_viewed_at'),
        migrations.RemoveField(model_name='article', name='last_viewed_at'),
    ]
```

## New Features in v0.2.0

### 1. Universal Stats Tag

```django
{% stats metric="views" period="today" output="text" %}
{% stats metric="unique_views" period="week" output="chart" %}
{% stats metric="all" period="month" output="widget" %}
{% stats metric="views" period="custom" start_date=start end_date=end output="json" %}
```

**Parameters:**
- `metric`: views, unique_views, all
- `period`: today, week, month, year, last_year, custom, total
- `output`: text, chart, json, widget, badge
- `chart_type`: line, bar, pie, area
- `chart_color`: hex color
- `obj`: object (auto-detected from context)

### 2. Automatic Middleware Tracking

No more `{% page_view_tracker %}` in every template! Middleware auto-injects tracking.

### 3. Extensible Architecture

Create custom implementations:

```python
# myapp/renderers.py
from djinsight.renderers import BaseRenderer

class CustomRenderer(BaseRenderer):
    def render(self):
        # Your custom rendering logic
        return f"Custom: {self.obj.total_views}"

# settings.py
DJINSIGHT = {
    'WIDGET_RENDERER': 'myapp.renderers.CustomRenderer',
}
```

### 4. Custom Providers

```python
# myapp/providers.py
from djinsight.providers.base import BaseProvider

class PostgreSQLProvider(BaseProvider):
    async def record_view(self, event_data):
        # Store directly in PostgreSQL instead of Redis
        pass

# settings.py
DJINSIGHT = {
    'PROVIDER_CLASS': 'myapp.providers.PostgreSQLProvider',
}
```

### 5. MCP-Style Registry

```python
from djinsight.registry import ProviderRegistry
from myapp.providers import CustomProvider

ProviderRegistry.register('custom', CustomProvider)
ProviderRegistry.set_default('custom')
```

## API Changes

### Querying Statistics

**OLD (v0.1.x):**
```python
article = Article.objects.get(pk=1)
print(article.total_views)  # Direct field access
print(article.get_views_today())  # Mixin method
```

**NEW (v0.2.0):**
```python
from djinsight.models import PageViewStatistics, StatsQueryMixin

article = Article.objects.get(pk=1)

# Get statistics object
stats = PageViewStatistics.get_for_object(article)
print(stats.total_views)
print(stats.unique_views)

# Use helper methods
views_today = StatsQueryMixin.get_views_today(article)
views_week = StatsQueryMixin.get_views_week(article, chart_data=True)
```

### Incrementing Views

**OLD:**
```python
article.increment_view_count(unique=True)
```

**NEW:**
```python
from djinsight.models import PageViewStatistics

stats = PageViewStatistics.get_or_create_for_object(article)
stats.increment_view_count(unique=True)
```

## Rollback Plan

If you need to rollback:

1. Restore backup:
```bash
python manage.py loaddata djinsight_backup.json
```

2. Reinstall v0.1.x:
```bash
pip install djinsight==0.1.9
```

3. Run migrations:
```bash
python manage.py migrate djinsight
```

## Support

- Issues: https://github.com/krystianmagdziarz/djinsight/issues
- Documentation: Will be available soon
- Changelog: See CHANGELOG.md

## Summary

v0.2.0 provides:
- ✅ Cleaner models (no mixins)
- ✅ Simpler templates (one universal tag)
- ✅ Automatic tracking (middleware)
- ✅ Full extensibility (custom implementations)
- ✅ Better performance (optimized indexes)
- ✅ Modern architecture (MCP-style)

Migration is straightforward and data is preserved!
