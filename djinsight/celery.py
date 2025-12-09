"""
Celery configuration for djinsight.

This module provides Celery configuration and periodic tasks for processing
page view statistics.
"""

import os

from celery import Celery
from celery.schedules import crontab
from django.conf import settings

from djinsight.conf import djinsight_settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "your_project.settings")

app = Celery("djinsight")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()


# Helper function to parse cron schedule from environment variables
def get_schedule_from_env(env_var, default_schedule):
    """
    Parse schedule from environment variable or return default.

    Environment variable can be:
    - "10" for every 10 seconds
    - "*/5" for every 5 minutes (cron format)
    - "0 1 * * *" for full cron expression
    """
    schedule_str = os.environ.get(env_var, None)
    if not schedule_str:
        return default_schedule

    # If it's just a number, treat as seconds
    if schedule_str.isdigit():
        return int(schedule_str)

    # If it contains spaces, treat as full cron expression
    if " " in schedule_str:
        parts = schedule_str.split()
        if len(parts) == 5:
            minute, hour, day, month, day_of_week = parts
            return crontab(
                minute=minute,
                hour=hour,
                day_of_month=day,
                month_of_year=month,
                day_of_week=day_of_week,
            )

    # If it contains */, treat as minute interval
    if "*/" in schedule_str:
        return crontab(minute=schedule_str)

    # If it's a single number without *, treat as minute interval
    if schedule_str.isdigit():
        return crontab(minute=f"*/{schedule_str}")

    return default_schedule


# Periodic tasks configuration with environment variable support
app.conf.beat_schedule = {
    "process-page-views": {
        "task": "djinsight.tasks.process_page_views_task",
        "schedule": get_schedule_from_env(
            "DJINSIGHT_PROCESS_SCHEDULE",
            10,
        ),
        "kwargs": {
            "batch_size": djinsight_settings.PROCESS_BATCH_SIZE,
            "max_records": djinsight_settings.PROCESS_MAX_RECORDS,
        },
    },
    "generate-daily-summaries": {
        "task": "djinsight.tasks.generate_daily_summaries_task",
        "schedule": get_schedule_from_env(
            "DJINSIGHT_SUMMARIES_SCHEDULE",
            crontab(minute="*/10"),
        ),
        "kwargs": {
            "days_back": djinsight_settings.SUMMARY_DAYS_BACK,
        },
    },
    "cleanup-old-data": {
        "task": "djinsight.tasks.cleanup_old_data_task",
        "schedule": get_schedule_from_env(
            "DJINSIGHT_CLEANUP_SCHEDULE",
            crontab(hour=1, minute=0),
        ),
        "kwargs": {
            "days_to_keep": djinsight_settings.CLEANUP_DAYS_TO_KEEP,
        },
    },
}

# Timezone configuration
app.conf.timezone = getattr(settings, "TIME_ZONE", "UTC")

# Additional Celery configuration
app.conf.update(
    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Task routing
    task_routes={
        "djinsight.tasks.*": {"queue": "djinsight"},
    },
    # Task execution
    task_always_eager=getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False),
    task_eager_propagates=True,
    # Worker configuration
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    # Result backend (optional)
    result_backend=getattr(settings, "CELERY_RESULT_BACKEND", None),
    result_expires=3600,  # 1 hour
)


@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery configuration."""
    print(f"Request: {self.request!r}")
    return "Debug task completed"


# Example of how to configure Celery in your Django settings:
"""
# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/1'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/1'

# djinsight specific settings
DJINSIGHT_BATCH_SIZE = 1000
DJINSIGHT_MAX_RECORDS = 10000
DJINSIGHT_SUMMARY_DAYS_BACK = 7
DJINSIGHT_DAYS_TO_KEEP = 90

# Redis settings for djinsight
DJINSIGHT_REDIS_HOST = 'localhost'
DJINSIGHT_REDIS_PORT = 6379
DJINSIGHT_REDIS_DB = 0
DJINSIGHT_REDIS_PASSWORD = None
DJINSIGHT_REDIS_KEY_PREFIX = 'djinsight:pageview:'
DJINSIGHT_REDIS_EXPIRATION = 60 * 60 * 24 * 7  # 7 days

# Enable/disable tracking
DJINSIGHT_ENABLE_TRACKING = True

# Celery Schedule Configuration (Environment Variables)
# DJINSIGHT_PROCESS_SCHEDULE = "10"        # Every 10 seconds (default)
# DJINSIGHT_SUMMARIES_SCHEDULE = "*/10"    # Every 10 minutes (default)
# DJINSIGHT_CLEANUP_SCHEDULE = "0 1 * * *"  # Daily at 1:00 AM (default)
"""
