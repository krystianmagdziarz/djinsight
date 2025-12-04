# Changelog

All notable changes to this project will be documented in this file.

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