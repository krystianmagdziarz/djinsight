## [0.3.3] - 2025-12-11

### Changed

- Minor release update

## [0.3.2] - 2025-12-11

### Added

- **🎨 Enhanced Template Tag System**
  - Added support for `metric="unique_views"` parameter in `{% stats %}` tag
  - New template examples for displaying unique view statistics
  - Unique views charts with customizable colors
  - Side-by-side comparison of total vs unique views

- **🔄 Async Redis Support**
  - New `AsyncRedisProvider` class for async Django views
  - Full async/await support using `redis.asyncio`
  - Parallel sync and async provider architecture
  - `ProviderRegistry` now returns appropriate provider based on `use_async` parameter

- **🤖 Enhanced MCP Responses**
  - MCP tools now include `object` field with human-readable object name (`__str__()`)
  - Better AI agent experience with readable object descriptions
  - All MCP responses include both IDs and descriptive names:
    - `get_page_stats` - includes object name
    - `get_top_pages` - includes object names for all results
    - `get_period_stats` - includes object name
  - Efficient bulk fetching for top pages

### Fixed

- **🐛 Critical: Unique Views Tracking**
  - Fixed unique views being counted multiple times for same session
  - Session keys now always marked in Redis (not only on first view)
  - Both `RedisProvider` and `AsyncRedisProvider` fixed
  - Proper distinction between total and unique view counters

- **🐛 Database Tasks**
  - Fixed `generate_daily_summaries` task with ContentType ID assignment
  - Proper ContentType instance fetching from `.values()` queries

### Enhanced

- **⚡ Generic Metric Support in Renderers**
  - `_render_text()` now supports any metric name dynamically
  - Forward-compatible with future metric additions
  - Automatic fallback for backward compatibility

### Technical Details

- Redis session keys now set on every view (prevents expiration issues)
- Async Redis uses connection pooling with lazy initialization
- Clean separation between sync `RedisProvider` and async `AsyncRedisProvider`
- No more coroutine errors in Celery tasks

## [0.3.1] - 2025-12-09

### Added

- MCP integration polishing and official djinsight-mcp MCP server example
- Updated README with Claude Desktop configuration

### Fixed

- MCP JSON Schema and JSON-RPC compatibility issues in tools definitions


# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0] - 2025-12-09

### Added

- **🔄 Async/Sync Provider Support**
  - `AsyncDatabaseProvider` - async wrapper for database operations
  - `ProviderRegistry.get_async_provider()` - convenience method
  - `USE_ASYNC` setting - toggle async/sync mode
  - Full async support via `asgiref.sync_to_async`
  - Compatible with Django async views

- **🤖 Model Context Protocol (MCP) Integration**
  - MCP server endpoint at `/djinsight/mcp/`
  - API key authentication via `MCPAPIKey` model
  - Four MCP tools:
    - `get_page_stats` - get statistics for specific object
    - `get_top_pages` - get top performing pages
    - `get_period_stats` - get statistics for time period
    - `list_tracked_models` - list all tracked content types
  - AI agents can now query djinsight statistics

- **✅ Comprehensive Test Suite**

### Changed

- **🏗️ Provider Architecture Refactored**
  - `BaseProvider` - now sync by default
  - `AsyncBaseProvider` - new async interface
  - Providers can implement both sync and async variants
  - Better separation of concerns

- **📝 Generic Naming Convention**
  - Changed `page_id` to `object_id` throughout codebase
  - More generic and applicable to any Django model
  - Consistent naming across all components

### Fixed

- Admin panel `view_ratio` display error with `format_html`
- Database access warnings in `AppConfig.ready()`
- Template tag object detection logic

## [0.2.0] - 2025-12-09

### 🚀 MAJOR REWRITE - Breaking Changes

**This is a complete architectural redesign. See MIGRATION_GUIDE.md for upgrading from v0.1.x**

### Added

- **🏗️ New Architecture - No More Mixins**
  - `ContentTypeRegistry` model for registering tracked models
  - `PageViewStatistics` model - statistics in separate table (no mixin needed!)
  - `PageViewEvent` model - replaces PageViewLog with ContentType support
  - Models are now completely clean - no need to pollute with mixin fields
  - Generic Foreign Key pattern for flexible object tracking

- **🎯 Universal Template Tag System**
  - ONE `{% stats %}` tag replaces 20+ redundant tags
  - Parameters: `metric`, `period`, `output`, `chart_type`, `chart_color`
  - Outputs: text, chart, json, widget, badge
  - Metrics: views, unique_views, all
  - Periods: today, week, month, year, last_year, custom, total
  - Example: `{% stats metric="views" period="week" output="chart" chart_type="line" %}`

- **🔌 Automatic Middleware Tracking**
  - `TrackingMiddleware` - auto-injects tracking scripts
  - No more manual `{% page_view_tracker %}` in every template
  - Configurable via `DJINSIGHT['AUTO_INJECT_TRACKING']`
  - Automatic object detection in view context

- **🎨 Extensible Architecture**
  - Custom renderers: `WIDGET_RENDERER`, `CHART_RENDERER`
  - Custom providers: `PROVIDER_CLASS` (Redis, PostgreSQL, etc.)
  - Custom middleware: `MIDDLEWARE_CLASS`
  - Custom processors: `EVENT_PROCESSOR`, `SESSION_TRACKER`
  - MCP-style provider registry system

- **📦 Settings Consolidation**
  - New `DJINSIGHT = {}` dict-based configuration
  - Backward compatible with old `DJINSIGHT_*` format
  - Cleaner, more organized settings structure
  - Extensible class references for custom implementations

- **🔧 Helper Functions & Utilities**
  - `get_stats_for_object(obj)` - quick stats access
  - `StatsQueryMixin` - reusable query methods
  - `format_view_count()` - smart number formatting
  - `check_stats_permission()` - permission checking

### Changed

- **💥 BREAKING: Removed PageViewStatisticsMixin**
  - Statistics now stored in separate `PageViewStatistics` table
  - No more mixin fields cluttering your models
  - Use `ContentTypeRegistry.register(YourModel)` instead
  - Migration tool provided: `python manage.py migrate_to_v2`

- **💥 BREAKING: Template Tags Redesigned**
  - Removed 20+ individual template tags
  - Replaced with universal `{% stats %}` tag
  - Old tags: `{% views_today_stat %}`, `{% unique_views_week_stat %}`, etc.
  - New tag: `{% stats metric="views" period="today" %}`

- **💥 BREAKING: Model Structure**
  - `PageViewLog` → `PageViewEvent` with ContentType support
  - `page_id` field → `content_type` + `object_id` (Generic FK)
  - Better support for multiple model types
  - Optimized database indexes

### Enhanced

- **⚡ Performance Improvements**
  - Comprehensive database indexes on all key fields
  - Optimized queries using `select_related` and `prefetch_related`
  - Efficient ContentType-based lookups
  - Better Redis key structure

- **🧪 Code Quality**
  - Pythonic code style (minimal comments, imports at top)
  - Type hints throughout codebase
  - Cleaner, more maintainable architecture
  - Better separation of concerns

### Removed

- **🗑️ Deprecated Features**
  - `PageViewStatisticsMixin` - use ContentTypeRegistry instead
  - All individual stat template tags - use `{% stats %}` instead
  - `page_view_tracker` tag - use middleware or `{% track %}`
  - Wagtail-specific tags - universal tags work for all models

### Migration

- **📦 Data Migration Tool**
  - `python manage.py migrate_to_v2` - automatic data migration
  - Migrates all PageViewLog → PageViewEvent
  - Migrates mixin statistics → PageViewStatistics
  - Auto-registers tracked models in ContentTypeRegistry
  - Supports `--dry-run` and `--batch-size` options

### Documentation

- **📖 Migration Guide**
  - Complete MIGRATION_GUIDE.md with step-by-step instructions
  - Code examples showing old vs new patterns
  - Rollback procedures
  - API changes documentation

### Technical Details

- **🏗️ Architecture**
  - Provider pattern for pluggable backends
  - Renderer pattern for flexible output
  - Registry pattern for centralized configuration
  - Middleware pattern for automatic tracking
  - MCP-inspired design for modularity

- **🗄️ Database Schema**
  - 10+ optimized indexes for performance
  - ContentType-based foreign keys
  - Proper unique constraints
  - Efficient querying patterns

### Notes

**IMPORTANT**: This is a major version with breaking changes. Existing v0.1.x installations must:
1. Read MIGRATION_GUIDE.md
2. Run `python manage.py migrate_to_v2`
3. Update template tags
4. Register models in ContentTypeRegistry
5. Remove mixin from models (optional, can be done later)

---

## [0.1.9] - 2025-12-08

### Added
- **📅 Extended Time Period Analytics**
  - New method `get_views_this_year()` - Get total views for the current year
  - New method `get_views_last_year()` - Get total views for the previous year
  - New method `get_views_for_period(start_date, end_date, unique=False)` - Get views for any custom date range with optional unique counting

- **👥 Unique Visitor Analytics**
  - New method `get_unique_views_today()` - Get unique visitors today
  - New method `get_unique_views_this_week()` - Get unique visitors this week
  - New method `get_unique_views_this_month()` - Get unique visitors this month
  - New method `get_unique_views_this_year()` - Get unique visitors this year
  - New method `get_unique_views_last_year()` - Get unique visitors last year

- **🏷️ New Template Tags**
  - `{% views_year_stat obj=article %}` - Display views this year statistic
  - `{% views_last_year_stat obj=article %}` - Display views last year statistic
  - `{% unique_views_today_stat obj=article %}` - Display unique views today
  - `{% unique_views_week_stat obj=article %}` - Display unique views this week
  - `{% unique_views_month_stat obj=article %}` - Display unique views this month
  - `{% unique_views_year_stat obj=article %}` - Display unique views this year
  - `{% unique_views_last_year_stat obj=article %}` - Display unique views last year
  - `{% views_custom_period_stat obj=article start_date=start end_date=end unique=True %}` - Display views for custom date range

- **📊 Interactive Charts & Visualization**
  - Integrated Chart.js 4.4.1 for beautiful, interactive analytics charts
  - Extended existing methods with `chart_data` parameter for unified API:
    - `get_views_today(chart_data=True)` - Hourly views for last 24 hours
    - `get_views_this_week(chart_data=True)` - Daily views for last 7 days
    - `get_views_this_month(chart_data=True)` - Daily views for last 30 days
    - `get_views_this_year(chart_data=True)` - Monthly views for last 12 months
  - Support for both total and unique visitor charts
  - Optimized chart data retrieval using PageViewSummary when available
  - Chart styling customization with `chart_type` ('line' or 'bar') and `chart_color` parameters

### Enhanced
- **🎨 Collapsible Stats Cards**
  - Redesigned `views_week_stat`, `views_month_stat`, `views_year_stat` with compact collapsible UI
  - Cards show summary stats inline: Total | Unique | Last viewed
  - Click to expand and reveal interactive chart
  - Charts lazy-load only when expanded for better performance
  - Cards positioned inline for horizontal layout

- **🎨 Page Analytics Widget**
  - Added support for `period='year'` parameter to display yearly statistics
  - Added support for `period='custom'` with `start_date` and `end_date` parameters for custom date ranges
  - Enhanced `page_analytics_widget` to automatically display appropriate statistics based on period
  - Added `show_charts=False` parameter to enable/disable chart visualizations
  - Example usage:
    ```django
    {% page_analytics_widget obj=article period='year' show_charts=True %}
    {% page_analytics_widget obj=article period='custom' start_date=start end_date=end %}
    ```

- **📈 Chart-Enabled Template Tags**
  - All period-specific tags now support chart visualization with styling options:
    - `{% views_week_stat obj=article show_chart=True chart_type='line' chart_color='#007bff' %}` - 7-day trend
    - `{% views_month_stat obj=article show_chart=True chart_type='bar' %}` - 30-day trend
    - `{% views_year_stat obj=article show_chart=True chart_color='#28a745' %}` - 12-month trend
  - Customizable chart types: 'line' (default for week/month) or 'bar' (default for year)
  - Custom color support via `chart_color` parameter (e.g., '#007bff', 'rgb(255, 99, 132)')
  - Charts automatically excluded for short periods (e.g., today) where they don't make sense
  - Responsive chart design adapts to mobile screens

### Removed
- **🗑️ Aggregate Stats Widget**
  - Removed `{% aggregate_stats_widget %}` template tag (redundant with individual stat cards)
  - Removed `aggregate_stats.html` template

### Technical Details
- **🔧 Database Query Optimization**
  - All unique views methods use `values('session_key').distinct().count()` for efficient unique counting
  - Custom period queries support both total and unique view counting
  - Proper date range filtering with `timestamp__gte` and `timestamp__lte`

- **🎨 Chart.js Integration**
  - CDN-loaded Chart.js 4.4.1 (no npm dependencies required)
  - Custom `DjInsightChart` JavaScript helper with utility functions:
    - `createLineChart()` - Create line/trend charts with customizable colors
    - `createBarChart()` - Create bar/column charts with customizable colors
    - `createMultiLineChart()` - Create multi-dataset comparison charts
  - Parameter-based architecture: existing methods like `get_views_this_week()` accept `chart_data=True` to return structured data for charts
  - Built-in color schemes with override support via `chart_color` parameter
  - Responsive design with mobile adaptations
  - New template filter `to_json` for safe JavaScript data serialization

### Documentation
- **📖 Template Updates**
  - Created 8 new template files in `djinsight/templates/djinsight/stats/`:
    - `views_year.html` - Year statistics template with optional chart
    - `views_last_year.html` - Last year statistics template
    - `unique_views_today.html` - Unique daily visitors template
    - `unique_views_week.html` - Unique weekly visitors template with optional chart
    - `unique_views_month.html` - Unique monthly visitors template with optional chart
    - `unique_views_year.html` - Unique yearly visitors template
    - `unique_views_last_year.html` - Unique last year visitors template
    - `views_custom_period.html` - Custom period statistics template
  - New `chart_base.html` - Shared Chart.js configuration and utilities

### Migration Notes
- **✅ Backward Compatibility**
  - All existing template tags and methods continue to work without modification
  - New features are additive and don't break existing functionality
  - Default behavior unchanged for existing implementations

## [0.1.8] - 2025-12-04

### Changed
- **🔧 Database Schema Update**
  - Increased `session_key` field length from 40 to 255 characters in `PageViewLog` model
  - Supports longer session keys for various session backends

## [0.1.7] - 2025-01-27

### Added
- **🌍 Environment Variable Configuration System**
  - Added `django-environ>=0.9.0` as a new dependency for environment variable management
  - All task parameters now configurable via environment variables:
    - `DJINSIGHT_BATCH_SIZE` - Number of records per processing batch (default: 1000)
    - `DJINSIGHT_MAX_RECORDS` - Maximum records per task run (default: 10000)
    - `DJINSIGHT_SUMMARY_DAYS_BACK` - Days back for summary generation (default: 1)
    - `DJINSIGHT_CLEANUP_DAYS_TO_KEEP` - Days to keep page view logs (default: 90)

- **⏱️ Celery Task Timeout Configuration**
  - Comprehensive timeout settings for all background tasks to prevent hanging workers
  - **Processing Task Timeouts:**
    - `DJINSIGHT_PROCESS_TASK_TIME_LIMIT` - Hard timeout (default: 1800s = 30 min)
    - `DJINSIGHT_PROCESS_TASK_SOFT_TIME_LIMIT` - Soft timeout (default: 1500s = 25 min)
  - **Summary Generation Timeouts:**
    - `DJINSIGHT_SUMMARY_TASK_TIME_LIMIT` - Hard timeout (default: 900s = 15 min)
    - `DJINSIGHT_SUMMARY_TASK_SOFT_TIME_LIMIT` - Soft timeout (default: 720s = 12 min)
  - **Cleanup Task Timeouts:**
    - `DJINSIGHT_CLEANUP_TASK_TIME_LIMIT` - Hard timeout (default: 3600s = 60 min)
    - `DJINSIGHT_CLEANUP_TASK_SOFT_TIME_LIMIT` - Soft timeout (default: 3300s = 55 min)

### Enhanced
- **🔧 Task Parameter Flexibility**
  - All Celery task functions now use `django-environ` for parameter defaults
  - Clean and elegant environment variable integration directly in function signatures
  - Maintains backward compatibility - parameters can still be passed directly
  - Environment variables override defaults but explicit parameters override environment variables

- **🛡️ Production Reliability**
  - Timeout configuration prevents runaway tasks from blocking Celery workers
  - Soft timeouts allow graceful task termination with cleanup
  - Hard timeouts ensure tasks are forcefully terminated if needed
  - Configurable timeouts adapt to different application scales and environments

### Documentation
- **📖 Complete Environment Configuration Guide**
  - Updated `docs/configuration.md` with comprehensive timeout and parameter documentation
  - Added environment variable examples for small and large applications
  - Production-ready Kubernetes deployment examples with full environment configuration
  - Enhanced `docs/quick-start.md` with performance tuning section
  - Updated `docs/installation.md` with new dependency requirements
  - Added environment configuration section to main README.md

### Technical Details
- **🏗️ Code Architecture Improvements**
  - Added `get_env_int()` helper function for safe environment variable parsing with validation
  - Enhanced error handling for invalid environment variable values
  - Comprehensive docstring updates for all task functions with environment variable documentation
  - Clean separation between task configuration and business logic

### Migration Notes
- **⚡ Zero Breaking Changes**
  - All existing configurations continue to work without modification
  - New environment variables provide additional configuration options
  - Default values match previous hardcoded values for seamless upgrades
  - Enhanced functionality is opt-in through environment variable configuration

## [0.1.6] - 2025-01-27

### Added
- **🚀 Database Performance Optimization**
  - Added optimized database indexes for improved query performance
  - New migration `0002_rename_djinsight_p_page_id_a3ba77_idx_djinsight_p_page_id_f86134_idx_and_more.py`
  - Enhanced database index naming for better clarity and management
  - Improved query performance for page view statistics retrieval

### Changed
- **📦 Package Version Update**
  - Version bump to 0.1.6 for new PyPI release
  - Updated package metadata across all configuration files
  - Maintained compatibility with existing installations


## [0.1.5] - 2025-01-27

### Changed
- **📦 Package Name Standardization**
  - Renamed package from `djInsight` to `djinsight` for Python naming convention compliance
  - Updated all internal references to use lowercase package name
  - Maintained backward compatibility for existing installations
  - No breaking changes - all import paths remain the same

### Documentation
- **📖 README Enhancements**
  - Added Django compatibility badges
  - Added Wagtail compatibility badges
  - Enhanced project metadata display

## [0.1.4] - 2025-01-27

### Added
- **⏰ Configurable Celery Task Schedules**
  - New environment variables for task scheduling configuration
  - `DJINSIGHT_PROCESS_SCHEDULE` - Configure page view processing frequency
  - `DJINSIGHT_SUMMARIES_SCHEDULE` - Configure summary generation frequency  
  - `DJINSIGHT_CLEANUP_SCHEDULE` - Configure cleanup task frequency
  - Support for seconds, cron minutes, and full cron expressions

### Changed
- **🔄 Default Task Schedules**
  - Process page views: Changed from every 5 minutes to every 10 seconds
  - Generate summaries: Changed from daily at 1:00 AM to every 10 minutes
  - Cleanup old data: Changed from weekly to daily at 1:00 AM
  - More frequent processing for better real-time performance

### Enhanced
- **🛠️ Schedule Flexibility**
  - Smart schedule parsing function `get_schedule_from_env()`
  - Support for multiple schedule formats:
    - Simple seconds: `"10"` = every 10 seconds
    - Cron minutes: `"*/5"` = every 5 minutes
    - Full cron: `"0 1 * * *"` = daily at 1:00 AM
  - Backward compatibility with existing configurations

### Documentation
- **📖 Configuration Guide Updates**
  - Complete documentation of new schedule settings
  - Environment variable configuration examples
  - Development, production, and Docker configuration samples
  - Schedule format reference with cron explanations
  - Integration examples for different deployment scenarios

## [0.1.3] - 2025-01-27

### Added
- **🔒 Permission Control System**
  - New `DJINSIGHT_ADMIN_ONLY` setting to restrict statistics access
  - Configurable access control for all template tags and API endpoints
  - Staff-only mode: only authenticated staff users can view statistics
  - Automatic permission checks in all template tags
  - Protected API endpoints with `@user_passes_test` decorator

### Enhanced
- **🛡️ Security Features**
  - Template-level permission validation
  - Graceful handling of permission denied scenarios
  - "Access denied" messages for unauthorized users
  - Backward compatibility with existing installations (default: open access)

### Documentation
- **📖 Permission Control Guide**
  - Complete documentation for permission system
  - Usage examples and configuration options
  - Security considerations and best practices
  - Migration guide for existing installations
  - Troubleshooting section for common issues

### Technical Details
- **🔧 Implementation**
  - `check_stats_permission()` function for view-level protection
  - `_check_stats_permission()` function for template-level protection
  - Updated all template tags to respect permission settings
  - Enhanced template rendering with `no_permission` flag
  - Comprehensive test suite for permission functionality

## [0.1.2] - 2025-06-07

### Added
- **📚 Comprehensive Documentation Structure**
  - Complete documentation reorganization into modular guides
  - Detailed Installation Guide with troubleshooting
  - Quick Start Guide with practical examples
  - Contributing guidelines for developers
  - License documentation with detailed explanations
  - Demo Gallery showcasing all features with screenshots

### Changed
- **📖 README Optimization**
  - Streamlined README with focus on quick overview
  - Reduced emoji usage for better readability
  - All detailed documentation moved to dedicated `docs/` folder
  - Enhanced "How It Works" section explaining two-tier architecture
  - Complete comparison with Google Analytics

### Enhanced
- **🎨 Documentation Experience**
  - Visual demo gallery with 5 comprehensive screenshots
  - Step-by-step guides for different use cases
  - Better navigation structure with clear links
  - Modular documentation that can be referenced independently

## [0.1.1] - 2025-06-07

### Added
- Modular HTML template system for statistics display
- Individual statistics components:
  - `total_views_stat` - Total views display component
  - `unique_views_stat` - Unique views display component  
  - `last_viewed_stat` - Last viewed timestamp component
  - `first_viewed_stat` - First viewed timestamp component
  - `views_today_stat` - Today's views component
  - `views_week_stat` - This week's views component
  - `views_month_stat` - This month's views component
  - `live_stats_counter` - Live counter with auto-refresh
- Enhanced Redis key structure with content_type identification
- Backward compatibility for existing Redis keys
- Content-type specific analytics for better object identification
- Example Django application with complete setup

### Changed
- **🔄 Template Tag Architecture Overhaul**
  - Replaced monolithic template with modular components
  - Each statistic now has its own dedicated template tag
  - Flexible composition system - mix and match components as needed
  - Improved template tag parameter consistency

### Enhanced
- **⚡ Redis Performance Optimizations**
  - Content-type specific key structure prevents ID conflicts
  - Enhanced key naming: `djinsight:counter:blog.article:123`
  - Automatic fallback to legacy key format for existing data
  - Better data organization and retrieval efficiency

### Fixed
- **🐛 Critical Bug Fixes**
  - Template tag context variable access (`obj._meta.label_lower` error)
  - Cross-model ID conflicts (Article ID=5 vs Product ID=5)
  - Browser cache affecting live statistics display
  - Request context availability in inclusion tags

### Development
- **🔧 Enhanced Development Experience**
  - Complete Celery integration with example project
  - Automated task scheduling (10s, 10min, daily intervals)
  - Comprehensive example project demonstrating all features
  - Better code organization following DRY principles
  - Enhanced debugging and logging capabilities

## [0.1.0] - 2025-06-06

### Added
- Initial release of djinsight
- Real-time page view tracking with Redis backend
- Django/Wagtail model integration via PageViewStatisticsMixin
- Session-based unique visitor tracking
- Celery integration for background data processing
- Basic template tags for analytics display
- Admin interface for viewing statistics
- Management commands for data processing and cleanup

### Features
- **High Performance**: Sub-millisecond page view recording using Redis
- **Real-time Statistics**: Live view counters with auto-refresh
- **Unique Visitor Tracking**: Session-based unique visitor detection
- **Data Aggregation**: Daily summaries for efficient historical queries
- **Automatic Cleanup**: Configurable data retention policies
- **Error Handling**: Robust error handling and logging
- **Scalability**: Designed for high-traffic websites
- **Flexibility**: Configurable settings for all aspects

### Models
- `PageViewStatisticsMixin` - Mixin for adding statistics to pages
- `PageViewLog` - Detailed individual page view logs
- `PageViewSummary` - Daily aggregated statistics

### API Endpoints
- `POST /djinsight/record-view/` - Record page views
- `POST /djinsight/page-stats/` - Get real-time statistics

### Configuration Options
- Redis connection settings
- Processing batch sizes and limits
- Data retention policies
- Tracking enable/disable
- Celery task scheduling

### Dependencies
- Django >= 3.2
- Wagtail >= 3.0
- Redis >= 4.0.0
- Celery >= 5.0.0

## [Unreleased]

### Planned Features
- Chart visualization widgets
- Export functionality for analytics data
- Advanced filtering and reporting
- Integration with Google Analytics
- Performance monitoring dashboard
- A/B testing support
- Geographic tracking (with privacy controls)
- Bot detection and filtering
- Custom event tracking
- REST API for external integrations

---

## Contributing

When contributing to this project, please:

1. Add new features under the `[Unreleased]` section
2. Follow the format: `### Added/Changed/Deprecated/Removed/Fixed/Security`
3. Include a brief description of the change
4. Reference any related issues or pull requests
5. Update the version number when releasing

## Release Process

1. Move items from `[Unreleased]` to a new version section
2. Update version numbers in `setup.py`, `pyproject.toml`, and `__init__.py`
3. Create a git tag for the release
4. Build and upload to PyPI
5. Update documentation