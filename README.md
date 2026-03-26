# djinsight

**Track page views. Query with AI.**

Your Django app's analytics, exposed to Claude and AI agents via MCP.

[![PyPI version](https://badge.fury.io/py/djinsight.svg)](https://badge.fury.io/py/djinsight)
[![Python](https://img.shields.io/pypi/pyversions/djinsight.svg)](https://pypi.org/project/djinsight/)

---

## The Problem

You want page view analytics. But you also want Claude to answer questions like:

> "What are my top 5 articles this week?"

Most analytics packages don't talk to AI. djinsight does.

---

## Installation

```bash
pip install djinsight
```

Add to `settings.py`:

```python
INSTALLED_APPS += ['djinsight']

DJINSIGHT = {
    'ENABLE_TRACKING': True,
    'USE_REDIS': False,
    'USE_CELERY': False,
}
```

Run migrations:

```bash
python manage.py migrate
```

Add URLs to `urls.py`:

```python
urlpatterns = [
    path('djinsight/', include('djinsight.urls')),
]
```

Done.

---

## Usage

### Track a page

Add to any template:

```django
{% load djinsight_tags %}
{% track %}
```

That's it. Views are now tracked.

### Display stats

```django
{% stats metric="views" period="week" %}
{% stats metric="views" period="week" output="chart" %}
```

---

## Connect to Claude

1. Install with MCP support:

```bash
pip install djinsight[mcp]
```

2. Add to Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
	"mcpServers": {
		"djinsight": {
			"command": "python",
			"args": ["-m", "djinsight.mcp"],
			"env": {
				"DJANGO_SETTINGS_MODULE": "your_project.settings"
			}
		}
	}
}
```

3. Restart Claude Desktop.

**13 tools available:**

- **Basic:** `get_page_stats`, `get_top_pages`, `list_tracked_models`
- **Periods:** `get_period_stats`, `compare_periods`
- **Trends:** `get_trending_pages`
- **Referrers:** `get_referrer_stats`, `get_traffic_sources`
- **Behavior:** `get_device_breakdown`, `get_hourly_pattern`
- **Cross-model:** `get_site_overview`, `compare_content_types`
- **Search:** `search_pages`

Now Claude can answer:

- "What are my top 10 pages this week?"
- "Where does my traffic come from?"
- "Which pages are trending up?"
- "Compare mobile vs desktop traffic"

---

## High Traffic?

Use Redis + Celery for async processing:

```python
DJINSIGHT = {
    'ENABLE_TRACKING': True,
    'USE_REDIS': True,
    'USE_CELERY': True,
    'REDIS_HOST': 'localhost',
}
```

Start Celery:

```bash
celery -A your_project worker -l info
celery -A your_project beat -l info
```

---

## Stats Tag Options

```django
{% stats metric="views" period="week" output="chart" chart_type="line" %}
```

| Parameter    | Options                                   |
| ------------ | ----------------------------------------- |
| `metric`     | `views`, `unique_views`                   |
| `period`     | `today`, `week`, `month`, `year`, `total` |
| `output`     | `text`, `chart`, `json`, `badge`          |
| `chart_type` | `line`, `bar`                             |

---

## Custom Backends

Swap any component:

```python
DJINSIGHT = {
    'PROVIDER_CLASS': 'myapp.providers.CustomProvider',
    'WIDGET_RENDERER': 'myapp.renderers.CustomRenderer',
}
```

---

## License

MIT

## Links

- [Issues](https://github.com/krystianmagdziarz/djinsight/issues)
- [CHANGELOG](CHANGELOG.md)
- [Migration Guide](MIGRATION_GUIDE.md)

## Sponsors

- [MDigital](https://mdigital.com.pl)
