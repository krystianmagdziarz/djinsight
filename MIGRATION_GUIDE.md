# Migration Guide: djinsight v0.1.x → v0.3.5

## Overview

Version 0.2.0+ is a **major rewrite** with significant architectural improvements. Version 0.3.5 further simplifies the setup by removing middleware and model registration requirements.

- No more mixins - statistics stored in separate tables
- ContentType-based tracking - track any model without modifying it
- One universal `{% stats %}` tag instead of 20+ redundant tags
- Simple `{% track %}` template tag for tracking (no middleware needed)
- No model registration required - just add `{% track %}` to templates
- Fully extensible architecture via settings
- MCP server for AI agent integration
- Async/sync provider support

## Breaking Changes

### 1. Model Changes

**OLD (v0.1.x):**
```python
from djinsight.models import PageViewStatisticsMixin

class Article(models.Model, PageViewStatisticsMixin):
    title = models.CharField(max_length=200)
    # Mixin added fields: total_views, unique_views, etc.
```

**NEW (v0.3.5):**
```python
# NO MIXIN NEEDED! Clean models
class Article(models.Model):
    title = models.CharField(max_length=200)

# Just add {% track %} to your template - that's it!
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

**NEW (v0.3.5):**
```django
{% load djinsight_tags %}

{# Add tracking to your template #}
{% track %}

{# ONE universal tag for stats! #}
{% stats metric="views" period="today" output="text" %}
{% stats metric="unique_views" period="week" output="chart" chart_type="line" %}
{% stats metric="views" period="month" output="widget" %}
{% stats metric="all" period="year" output="json" %}
```

### 3. Settings Structure

**OLD (v0.1.x):**
```python
DJINSIGHT_ENABLE_TRACKING = True
DJINSIGHT_ADMIN_ONLY = False
DJINSIGHT_REDIS_HOST = 'localhost'
# ... many separate settings
```

**NEW (v0.3.5):**
```python
DJINSIGHT = {
    # Core settings
    'ENABLE_TRACKING': True,
    'ADMIN_ONLY': False,

    # Synchronous mode (no Redis/Celery needed)
    'USE_REDIS': False,
    'USE_CELERY': False,

    # Or async mode with Redis + Celery:
    # 'USE_REDIS': True,
    # 'USE_CELERY': True,
    # 'REDIS_HOST': 'localhost',
    # 'REDIS_PORT': 6379,
    # 'REDIS_URL': None,  # or 'redis://localhost:6379/0' for cloud
    # 'REDIS_DB': 0,
    # 'REDIS_PASSWORD': None,

    # Extensibility
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

### 4. Middleware Removed (v0.3.5)

If you added `TrackingMiddleware` in v0.2.0, **remove it** - it no longer exists in v0.3.5:

```python
# REMOVE this from MIDDLEWARE:
# 'djinsight.middleware.TrackingMiddleware',
```

Use `{% track %}` template tag instead.

### 5. Model Registration Removed (v0.3.5)

`ContentTypeRegistry.register()` is no longer required. Just add `{% track %}` to your template. `ContentTypeRegistry` is now optional (for admin visibility only).

## Migration Steps

### Step 1: Backup Your Database

```bash
python manage.py dumpdata djinsight > djinsight_backup.json
```

### Step 2: Install djinsight v0.3.5

```bash
pip install djinsight==0.3.5
```

### Step 3: Run New Migrations

```bash
python manage.py migrate djinsight
```

This automatically:
- Creates new tables (`ContentTypeRegistry`, `PageViewStatistics`, `PageViewEvent`)
- Converts `PageViewSummary.content_type` from string to ForeignKey (data preserved)
- Migrates mixin statistics (total_views, unique_views, etc.) to `PageViewStatistics` table
- Renames `page_id` to `object_id` in `PageViewSummary`

### Step 4: Run Data Migration Command (Optional)

If the automatic migration didn't catch all your data (e.g., PageViewLog records), run:

```bash
# Dry run first
python manage.py migrate_to_v2 --dry-run

# Actual migration
python manage.py migrate_to_v2

# With custom batch size
python manage.py migrate_to_v2 --batch-size=500
```

### Step 5: Update Your Code

#### Remove Mixin from Models

```python
# OLD
from djinsight.models import PageViewStatisticsMixin

class Article(models.Model, PageViewStatisticsMixin):
    title = models.CharField(max_length=200)

# NEW - clean!
class Article(models.Model):
    title = models.CharField(max_length=200)
```

#### Update Templates

Replace old tags with universal `{% stats %}` and `{% track %}`:

```django
{% load djinsight_tags %}

{# Replace {% page_view_tracker %} with: #}
{% track %}

{# Replace individual stat tags: #}
{% stats metric="views" period="week" output="chart" chart_type="line" chart_color="#007bff" %}
```

#### Accessing View Counts in Custom Templates

If you previously accessed `article.total_views` directly (from the mixin), use `PageViewStatistics`:

```python
from djinsight.models import PageViewStatistics

stats = PageViewStatistics.get_for_object(article)
total = stats.total_views if stats else 0
unique = stats.unique_views if stats else 0
```

Or create template filters:

```python
from django import template
from djinsight.models import PageViewStatistics

register = template.Library()

@register.filter
def total_views(obj):
    try:
        stats = PageViewStatistics.get_for_object(obj)
        return stats.total_views if stats else 0
    except Exception:
        return 0

@register.filter
def unique_views(obj):
    try:
        stats = PageViewStatistics.get_for_object(obj)
        return stats.unique_views if stats else 0
    except Exception:
        return 0
```

Then in templates: `{{ article|total_views }}` instead of `{{ article.total_views }}`.

#### Update Settings

```python
DJINSIGHT = {
    'ENABLE_TRACKING': True,
    'USE_REDIS': False,   # Direct database writes
    'USE_CELERY': False,  # No background processing
}
```

#### Remove Celery Beat Tasks (if disabling async)

Remove djinsight tasks from your Celery beat schedule:

```python
# REMOVE these from app.conf.beat_schedule:
# "process-page-views": { "task": "djinsight.tasks.process_page_views_task", ... },
# "cleanup-old-data": { "task": "djinsight.tasks.cleanup_old_data_task", ... },
```

#### Remove TrackingMiddleware (if present)

```python
# REMOVE from MIDDLEWARE:
# 'djinsight.middleware.TrackingMiddleware',
```

### Step 6: Create Migration for Removing Mixin Fields

Once you've verified everything works, remove the old mixin fields:

```bash
python manage.py makemigrations yourapp --name remove_pageview_mixin_fields
python manage.py migrate
```

## New Features

### Universal Stats Tag

```django
{% stats metric="views" period="today" output="text" %}
{% stats metric="unique_views" period="week" output="chart" %}
{% stats metric="views" period="custom" start_date=start end_date=end output="json" %}
```

| Parameter    | Options                                       |
|-------------|-----------------------------------------------|
| `metric`    | `views`, `unique_views`                       |
| `period`    | `today`, `week`, `month`, `year`, `total`     |
| `output`    | `text`, `chart`, `json`, `badge`              |
| `chart_type`| `line`, `bar`                                 |

### MCP Server (v0.3.0+)

AI agents can query your analytics:

1. Create API key in Django admin: `/admin/djinsight/mcpapikey/`
2. Configure Claude Desktop with the MCP server
3. Ask Claude: "What are my top 10 pages this week?"

### Async Support (v0.3.0+)

- `AsyncDatabaseProvider` for async Django views
- `AsyncRedisProvider` for async Redis operations
- `REDIS_URL` environment variable support for cloud deployments

## API Changes

### Querying Statistics

**OLD (v0.1.x):**
```python
article.total_views        # Direct field access
article.get_views_today()  # Mixin method
```

**NEW (v0.3.5):**
```python
from djinsight.models import PageViewStatistics

stats = PageViewStatistics.get_for_object(article)
stats.total_views
stats.unique_views
```

## Rollback Plan

1. Restore backup:
```bash
python manage.py loaddata djinsight_backup.json
```

2. Reinstall v0.1.9:
```bash
pip install djinsight==0.1.9
```

3. Run migrations:
```bash
python manage.py migrate djinsight
```

## Support

- Issues: https://github.com/krystianmagdziarz/djinsight/issues
- Changelog: See CHANGELOG.md
