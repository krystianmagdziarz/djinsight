# Advanced MCP Server for djinsight

## Overview

Replace the current custom HTTP endpoint + Node.js wrapper with a native Python MCP server using the official `mcp` SDK. Expand from 4 basic read-only tools to 13 analytics-focused tools covering trends, referrers, behavior, and cross-model analysis.

## Current State

- 4 basic tools: `get_page_stats`, `get_top_pages`, `get_period_stats`, `list_tracked_models`
- Custom HTTP endpoint in `djinsight/mcp/server.py` with `mcp_endpoint` Django view
- Node.js wrapper in `mcp-package/` that proxies stdio to HTTP
- Authentication via `MCPAPIKey` model

## Target Architecture

Native Python MCP server using `mcp` SDK with stdio transport. No Node.js dependency. Direct Django ORM access.

### Directory Structure

```
djinsight/mcp/
├── __init__.py
├── __main__.py          # entry point: python -m djinsight.mcp
├── server.py            # MCP server registration, stdio transport
├── tools/
│   ├── __init__.py
│   ├── basic.py         # get_page_stats, get_top_pages, list_tracked_models
│   ├── periods.py       # get_period_stats, compare_periods
│   ├── trends.py        # get_trending_pages
│   ├── referrers.py     # get_referrer_stats, get_traffic_sources
│   ├── behavior.py      # get_device_breakdown, get_hourly_pattern
│   ├── cross_model.py   # get_site_overview, compare_content_types
│   └── search.py        # search_pages
└── utils.py             # parse_content_type, user_agent parsing, date helpers
```

### Tools (13 total)

#### Basic (improved):
1. **get_page_stats** - Stats for a specific object (total/unique views, first/last viewed)
2. **get_top_pages** - Top pages by views, with optional period filter
3. **list_tracked_models** - All tracked content types with config
4. **get_period_stats** - Stats for a period, supports custom date ranges

#### Trends & Comparisons:
5. **compare_periods** - Compare two periods (e.g. this week vs last week), returns growth rate and delta
6. **get_trending_pages** - Pages with biggest growth/decline in a period

#### Traffic Sources:
7. **get_referrer_stats** - Top referrers per object or content type, grouped by domain
8. **get_traffic_sources** - Aggregated sources (direct, search, social, referral)

#### Behavioral:
9. **get_device_breakdown** - Mobile vs desktop vs tablet (user agent parsing)
10. **get_hourly_pattern** - Hourly traffic distribution

#### Cross-model:
11. **get_site_overview** - Total site-wide stats across all content types
12. **compare_content_types** - Compare traffic between content types

#### Utility:
13. **search_pages** - Search objects by name/title with their stats

### Entry Point

```bash
python -m djinsight.mcp
```

Requires `DJANGO_SETTINGS_MODULE` env var. Claude Desktop config:

```json
{
  "mcpServers": {
    "djinsight": {
      "command": "python",
      "args": ["-m", "djinsight.mcp"],
      "env": {
        "DJANGO_SETTINGS_MODULE": "myproject.settings"
      }
    }
  }
}
```

### Removals

- `mcp-package/` (Node.js wrapper) - no longer needed
- `mcp_endpoint` Django view - replaced by native MCP
- `MCPAPIKey` model - not needed for stdio transport (local process)
- MCP URL pattern from `urls.py`

### Dependencies

- Add `mcp` to optional dependencies: `pip install djinsight[mcp]`
- User agent parsing: lightweight regex in `utils.py`, no external deps

### Trade-offs

- **Pro:** Zero Node.js, native Django ORM, simpler stack, richer analytics
- **Con:** Requires Python env with Django+djinsight installed (standard for MCP servers)
