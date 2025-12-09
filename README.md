# djinsight

**MCP-first analytics for Django** - Expose your Django app statistics to Claude and other AI agents through Model Context Protocol.

[![PyPI version](https://badge.fury.io/py/djinsight.svg)](https://badge.fury.io/py/djinsight)
[![Python](https://img.shields.io/pypi/pyversions/djinsight.svg)](https://pypi.org/project/djinsight/)
[![Django](https://img.shields.io/badge/Django-3.2%20%7C%204.x%20%7C%205.x-green.svg)](https://www.djangoproject.com/)

## Why djinsight?

**Built for AI-first workflows.** djinsight is the first Django analytics package designed with MCP (Model Context Protocol) as a primary interface. Claude, other AI agents, or automation tools can query your app's analytics directly.

## Quick Start

```bash
pip install djinsight
```

### Option 1: Synchronous (No Redis/Celery)

**Direct database writes - simplest setup:**

```python
# settings.py
INSTALLED_APPS = ['djinsight']
MIDDLEWARE = ['djinsight.middleware.TrackingMiddleware']

DJINSIGHT = {
    'ENABLE_TRACKING': True,
    'USE_REDIS': False,  # Direct to database
    'USE_CELERY': False,
}
```

### Option 2: Async with Redis + Celery (Recommended)

**High-performance buffered writes:**

```python
# settings.py
INSTALLED_APPS = ['djinsight']
MIDDLEWARE = ['djinsight.middleware.TrackingMiddleware']

DJINSIGHT = {
    'ENABLE_TRACKING': True,
    'USE_REDIS': True,   # Buffer in Redis
    'USE_CELERY': True,  # Process with Celery
    'REDIS_HOST': 'localhost',
    'REDIS_PORT': 6379,
}
```

**Start Celery worker:**
```bash
celery -A your_project worker -l info
celery -A your_project beat -l info
```

### Register Models

```python
# blog/apps.py
from django.apps import AppConfig

class BlogConfig(AppConfig):
    name = 'blog'

    def ready(self):
        from djinsight.models import ContentTypeRegistry
        from blog.models import Article
        ContentTypeRegistry.register(Article)
```

### Use in Templates

```django
{% load djinsight_tags %}

{% stats metric="views" period="week" output="chart" %}
{% stats metric="unique_views" period="today" output="badge" %}
```

## Configuration Modes

| Feature | Synchronous | Async (Redis+Celery) |
|---------|-------------|---------------------|
| **Setup** | ✅ Simple | ⚙️ Requires Redis+Celery |
| **Dependencies** | None | Redis, Celery |
| **Performance** | Good | Excellent |
| **Request blocking** | ~5ms | <1ms |
| **Batch processing** | ❌ No | ✅ Yes |
| **Recommended for** | Small sites, dev | Production, high traffic |

**Switch modes anytime:**
```python
DJINSIGHT = {
    'USE_REDIS': False,  # False = sync, True = async
}
```

## MCP Integration (Claude Desktop)

**Works with both local and remote Django servers:**

1. **Create API key** in Django admin (`/admin/djinsight/mcpapikey/`)

2. **Install djinsight-mcp** (local package):

```bash
cd /path/to/djinsight/mcp-package
npm install
```

3. **Configure Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "djinsight": {
      "command": "node",
      "args": ["/path/to/djinsight/mcp-package/index.js"],
      "env": {
        "DJINSIGHT_URL": "http://localhost:8001",
        "DJINSIGHT_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```

4. **Restart Claude Desktop**

**Available MCP tools:**
- `get_page_stats` - Get statistics for specific object  
- `get_top_pages` - Get top performing pages
- `get_period_stats` - Get time period statistics  
- `list_tracked_models` - List all tracked models

### Example Claude Interaction

```
You: "What are my top 5 blog articles this week?"

Claude: [Uses get_top_pages tool]
"Your top articles:
1. 'Django Performance Tips' - 1,247 views (823 unique)
2. 'Redis Caching Guide' - 891 views (654 unique)
3. 'API Design Patterns' - 743 views (521 unique)
4. 'Docker for Django' - 612 views (445 unique)
5. 'Testing Best Practices' - 502 views (389 unique)"

You: "Show me detailed stats for article #1"

Claude: [Uses get_page_stats + get_period_stats]
"Django Performance Tips (ID: 1):
- Total views: 3,452
- Unique visitors: 2,103
- First viewed: 2024-11-15
- Last viewed: 2 hours ago
- This week: 1,247 views"
```

## Universal Stats Tag

```django
{% stats metric="views" period="week" output="chart" chart_type="line" %}
```

**Parameters:**
- `metric`: `views`, `unique_views`
- `period`: `today`, `week`, `month`, `year`, `last_year`, `custom`, `total`
- `output`: `text`, `chart`, `json`, `widget`, `badge`
- `chart_type`: `line`, `bar`

## Extensibility

Everything is swappable via settings:

```python
DJINSIGHT = {
    'WIDGET_RENDERER': 'myapp.renderers.CustomRenderer',
    'CHART_RENDERER': 'myapp.renderers.CustomChartRenderer',
    'PROVIDER_CLASS': 'myapp.providers.PostgreSQLProvider',
    'MIDDLEWARE_CLASS': 'myapp.middleware.CustomTracking',
}
```

**Custom renderer:**

```python
from djinsight.renderers import BaseRenderer

class CustomRenderer(BaseRenderer):
    def render(self):
        data = self.get_data()
        return f"<div>Views: {data.get('total_views', 0)}</div>"
```

**Custom provider (replace Redis):**

```python
from djinsight.providers.base import BaseProvider

class PostgreSQLProvider(BaseProvider):
    async def record_view(self, event_data):
        # Direct PostgreSQL writes instead of Redis buffering
        pass
```

## Upgrading

See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for v0.1.x → v0.2.0 migration steps.

## License

MIT

## Links

- [Documentation](https://github.com/krystianmagdziarz/djinsight)
- [Issues](https://github.com/krystianmagdziarz/djinsight/issues)
- [CHANGELOG](CHANGELOG.md)
