from typing import Any, Callable

from django.conf import settings
from django.utils.module_loading import import_string


class DjInsightSettings:
    DEFAULTS = {
        "ENABLE_TRACKING": True,
        "AUTO_INJECT_TRACKING": True,
        "ADMIN_ONLY": False,
        "REDIS_HOST": "localhost",
        "REDIS_PORT": 6379,
        "REDIS_DB": 0,
        "REDIS_PASSWORD": None,
        "REDIS_TIMEOUT": 5,
        "REDIS_CONNECT_TIMEOUT": 5,
        "REDIS_KEY_PREFIX": "djinsight:pageview:",
        "REDIS_EXPIRATION": 60 * 60 * 24 * 7,
        "TRACK_MODELS": [],
        "TRACK_ANONYMOUS": True,
        "TRACK_AUTHENTICATED": True,
        "TRACK_STAFF": True,
        "TRACK_SUPERUSER": True,
        "MIDDLEWARE_CLASS": "djinsight.middleware.TrackingMiddleware",
        "STATS_TAG_FUNCTION": "djinsight.templatetags.djinsight_tags.stats",
        "WIDGET_RENDERER": "djinsight.renderers.DefaultWidgetRenderer",
        "CHART_RENDERER": "djinsight.renderers.DefaultChartRenderer",
        "PROVIDER_CLASS": None,
        "REGISTRY_CLASS": "djinsight.registry.ProviderRegistry",
        "EVENT_PROCESSOR": "djinsight.processors.DefaultEventProcessor",
        "SESSION_TRACKER": "djinsight.trackers.SessionTracker",
        "IP_EXTRACTOR": "djinsight.utils.get_client_ip",
        "USER_AGENT_PARSER": "djinsight.utils.parse_user_agent",
        "USE_REDIS": True,
        "USE_CELERY": True,
        "USE_ASYNC": False,  # Use async provider (for async Django views)
        "ASYNC_PROCESSING": True,
        "RETENTION_DAYS": 365,
        "SUMMARY_RETENTION_DAYS": 730,
        "CLEANUP_BATCH_SIZE": 1000,
        "PROCESS_BATCH_SIZE": 100,
        "PROCESS_MAX_RECORDS": 10000,
        "PROCESS_TASK_TIME_LIMIT": 1800,
        "PROCESS_TASK_SOFT_TIME_LIMIT": 1500,
        "SUMMARY_TASK_TIME_LIMIT": 900,
        "SUMMARY_TASK_SOFT_TIME_LIMIT": 720,
        "CLEANUP_TASK_TIME_LIMIT": 3600,
        "CLEANUP_TASK_SOFT_TIME_LIMIT": 3300,
        "SUMMARY_DAYS_BACK": 7,
        "CLEANUP_DAYS_TO_KEEP": 90,
        "CACHE_TTL": 300,
        "ENABLE_CACHING": True,
        "CACHE_BACKEND": "default",
        "PRIVACY_MODE": False,
        "ANONYMIZE_IP": False,
        "STORE_USER_AGENT": True,
        "STORE_REFERRER": True,
        "CELERY_TASK_TIME_LIMIT": 600,
        "CELERY_TASK_SOFT_TIME_LIMIT": 540,
        "MCP_ENABLED": True,
        "MCP_ENDPOINT_URL": "/djinsight/mcp/",
        "MCP_API_KEY_HEADER": "Authorization",
        "MCP_RATE_LIMIT": 100,
        "MCP_RATE_LIMIT_PERIOD": 60,
    }

    def __getattr__(self, name: str) -> Any:
        if name not in self.DEFAULTS:
            raise AttributeError(f"Invalid setting: {name}")

        user_settings = getattr(settings, "DJINSIGHT", {})

        if name in user_settings:
            return user_settings[name]

        legacy_key = f"DJINSIGHT_{name}"
        if hasattr(settings, legacy_key):
            return getattr(settings, legacy_key)

        return self.DEFAULTS[name]

    def get_class(self, setting_name: str) -> Callable:
        class_path = getattr(self, setting_name)
        return import_string(class_path)

    def get_middleware_class(self):
        return self.get_class("MIDDLEWARE_CLASS")

    def get_provider_class(self):
        provider_class_path = getattr(self, "PROVIDER_CLASS")
        if provider_class_path is None:
            if self.USE_REDIS:
                return import_string("djinsight.providers.redis.RedisProvider")
            else:
                return import_string("djinsight.providers.database.DatabaseProvider")
        return import_string(provider_class_path)

    def get_registry_class(self):
        return self.get_class("REGISTRY_CLASS")

    def get_widget_renderer(self):
        return self.get_class("WIDGET_RENDERER")

    def get_chart_renderer(self):
        return self.get_class("CHART_RENDERER")

    def get_event_processor(self):
        return self.get_class("EVENT_PROCESSOR")

    def get_session_tracker(self):
        return self.get_class("SESSION_TRACKER")

    def get_ip_extractor(self):
        return self.get_class("IP_EXTRACTOR")

    def get_user_agent_parser(self):
        return self.get_class("USER_AGENT_PARSER")

    def should_track_user(self, user) -> bool:
        if not user:
            return self.TRACK_ANONYMOUS

        if not user.is_authenticated:
            return self.TRACK_ANONYMOUS

        if user.is_superuser and not self.TRACK_SUPERUSER:
            return False

        if user.is_staff and not self.TRACK_STAFF:
            return False

        return self.TRACK_AUTHENTICATED


djinsight_settings = DjInsightSettings()
