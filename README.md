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

1. Create API key in Django admin: `/admin/djinsight/mcpapikey/`

2. Install the MCP package:

```bash
cd /path/to/djinsight/mcp-package
npm install
```

3. Add to Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
	"mcpServers": {
		"djinsight": {
			"command": "node",
			"args": ["/path/to/djinsight/mcp-package/index.js"],
			"env": {
				"DJINSIGHT_URL": "http://localhost:8000",
				"DJINSIGHT_API_KEY": "your_api_key"
			}
		}
	}
}
```

4. Restart Claude Desktop.

Now Claude can answer:

- "What are my top 10 pages?"
- "How many views did article #5 get this week?"
- "Show me view trends for the homepage"

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
