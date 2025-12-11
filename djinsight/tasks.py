import json
import logging
from datetime import datetime, timedelta

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone
from redis.exceptions import ConnectionError, TimeoutError

from djinsight.conf import djinsight_settings
from djinsight.models import PageViewEvent, PageViewStatistics, PageViewSummary
from djinsight.providers.redis import RedisProvider

logger = logging.getLogger(__name__)

redis_provider = RedisProvider()
redis_client = redis_provider.client
REDIS_KEY_PREFIX = djinsight_settings.REDIS_KEY_PREFIX

# Try to import Celery - if not available, tasks will be regular functions
try:
    from celery import shared_task

    HAS_CELERY = True
except ImportError:
    # Fallback decorator for when Celery is not available
    def shared_task(func):
        return func

    HAS_CELERY = False


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    task_time_limit=djinsight_settings.PROCESS_TASK_TIME_LIMIT,
    task_soft_time_limit=djinsight_settings.PROCESS_TASK_SOFT_TIME_LIMIT,
)
def process_page_views_task(
    self,
    batch_size=None,
    max_records=None,
):
    """
    Celery task to process page views from Redis and store them in the database.

    Args:
        batch_size (int): Number of records to process in a single transaction
        max_records (int): Maximum number of records to process in a single run

    Returns:
        int: Number of records processed
    """
    try:
        batch_size = batch_size or djinsight_settings.PROCESS_BATCH_SIZE
        max_records = max_records or djinsight_settings.PROCESS_MAX_RECORDS
        return process_page_views(batch_size, max_records)
    except Exception as exc:
        logger.error(f"Error processing page views: {exc}")
        if HAS_CELERY:
            raise self.retry(exc=exc)
        else:
            raise


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    task_time_limit=djinsight_settings.SUMMARY_TASK_TIME_LIMIT,
    task_soft_time_limit=djinsight_settings.SUMMARY_TASK_SOFT_TIME_LIMIT,
)
def generate_daily_summaries_task(
    self, days_back=None
):
    """
    Celery task to generate daily page view summaries.

    Args:
        days_back (int): Number of days back to process

    Returns:
        int: Number of summaries generated
    """
    try:
        days_back = days_back or djinsight_settings.SUMMARY_DAYS_BACK
        return generate_daily_summaries(days_back)
    except Exception as exc:
        logger.error(f"Error generating daily summaries: {exc}")
        if HAS_CELERY:
            raise self.retry(exc=exc)
        else:
            raise


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    task_time_limit=djinsight_settings.CLEANUP_TASK_TIME_LIMIT,
    task_soft_time_limit=djinsight_settings.CLEANUP_TASK_SOFT_TIME_LIMIT,
)
def cleanup_old_data_task(
    self, days_to_keep=None
):
    """
    Celery task to cleanup old page view logs.

    Args:
        days_to_keep (int): Number of days of logs to keep

    Returns:
        int: Number of records deleted
    """
    try:
        days_to_keep = days_to_keep or djinsight_settings.CLEANUP_DAYS_TO_KEEP
        return cleanup_old_data(days_to_keep)
    except Exception as exc:
        logger.error(f"Error cleaning up old data: {exc}")
        if HAS_CELERY:
            raise self.retry(exc=exc)
        else:
            raise


def process_page_views(
    batch_size=None,
    max_records=None,
):
    """
    Process page views from Redis and store them in the database.

    Args:
        batch_size (int): Number of records to process in a single transaction
        max_records (int): Maximum number of records to process in a single run

    Returns:
        int: Number of records processed
    """
    batch_size = batch_size or djinsight_settings.PROCESS_BATCH_SIZE
    max_records = max_records or djinsight_settings.PROCESS_MAX_RECORDS
    if not redis_client:
        logger.error("Redis client not available")
        return 0

    logger.info("Starting to process page views from Redis")

    try:
        # Get all keys matching the page view pattern, excluding counters and sessions
        pattern = f"{REDIS_KEY_PREFIX}*"
        exclude_patterns = [
            f"{REDIS_KEY_PREFIX}counter:",
            f"{REDIS_KEY_PREFIX}unique_counter:",
            f"{REDIS_KEY_PREFIX}session:",
        ]

        # Get all keys
        all_keys = redis_client.keys(pattern)
        # Filter out counter and session keys
        keys = [
            key.decode("utf-8")
            for key in all_keys
            if not any(
                key.decode("utf-8").startswith(exclude) for exclude in exclude_patterns
            )
        ]

        # Limit the number of keys to process
        keys = keys[:max_records]

        if not keys:
            logger.info("No page views to process")
            return 0

        logger.info(f"Found {len(keys)} page views to process")

        # Process in batches
        processed_count = 0
        for i in range(0, len(keys), batch_size):
            batch_keys = keys[i : i + batch_size]
            batch_processed = process_batch(batch_keys)
            processed_count += batch_processed

            # Log progress
            if i % (batch_size * 10) == 0:
                logger.info(f"Processed {processed_count} / {len(keys)} page views")

        logger.info(f"Completed processing {processed_count} page views")
        return processed_count

    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Redis connection error: {e}")
        raise
    except Exception as e:
        logger.error(f"Error processing page views: {e}")
        raise


def process_batch(keys):
    """
    Process a batch of page views.

    Args:
        keys (list): List of Redis keys to process

    Returns:
        int: Number of records processed in this batch
    """
    if not redis_client:
        return 0

    pipe = redis_client.pipeline()
    for key in keys:
        pipe.get(key)
    values = pipe.execute()

    page_view_events = []
    page_view_counters = {}
    processed_count = 0

    for key, value in zip(keys, values):
        if value is None:
            continue

        try:
            data = json.loads(value.decode("utf-8"))

            # Extract data with validation
            page_id = data.get("object_id")
            content_type = data.get("content_type")
            url = data.get("url")
            session_key = data.get("session_key")
            ip_address = data.get("ip_address")
            user_agent = data.get("user_agent")
            referrer = data.get("referrer")
            timestamp_value = data.get("timestamp")
            is_unique = data.get("is_unique", False)

            # Skip if missing essential data
            if not all([page_id, content_type, url]):
                logger.warning(f"Skipping incomplete page view data in key {key}")
                continue

            # Convert timestamp
            if timestamp_value:
                if isinstance(timestamp_value, str):
                    timestamp = datetime.fromtimestamp(
                        int(timestamp_value), tz=timezone.get_current_timezone()
                    )
                else:
                    timestamp = datetime.fromtimestamp(
                        timestamp_value, tz=timezone.get_current_timezone()
                    )
            else:
                timestamp = timezone.now()

            app_label, model = content_type.split(".")
            ct = ContentType.objects.get_by_natural_key(app_label, model)

            page_view_events.append(
                PageViewEvent(
                    content_type=ct,
                    object_id=page_id,
                    url=url,
                    session_key=session_key[:255] if session_key else "",
                    ip_address=ip_address,
                    user_agent=user_agent[:1000] if user_agent else "",
                    referrer=referrer[:500] if referrer else "",
                    timestamp=timestamp,
                    is_unique=is_unique,
                )
            )

            counter_key = (ct.id, page_id)
            if counter_key not in page_view_counters:
                page_view_counters[counter_key] = (1, 1 if is_unique else 0)
            else:
                total, unique = page_view_counters[counter_key]
                page_view_counters[counter_key] = (
                    total + 1,
                    unique + (1 if is_unique else 0),
                )

            processed_count += 1

        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.error(f"Error processing page view {key}: {e}")
            continue
        except Exception as e:
            logger.error(f"Unexpected error processing page view {key}: {e}")
            continue

    if page_view_events or page_view_counters:
        with transaction.atomic():
            if page_view_events:
                PageViewEvent.objects.bulk_create(page_view_events, batch_size=500)

            for (content_type_id, object_id), (total, unique) in page_view_counters.items():
                try:
                    stats, created = PageViewStatistics.objects.get_or_create(
                        content_type_id=content_type_id,
                        object_id=object_id,
                    )
                    stats.total_views += total
                    stats.unique_views += unique
                    stats.last_viewed_at = timezone.now()
                    if not stats.first_viewed_at:
                        stats.first_viewed_at = timezone.now()
                    stats.save(update_fields=['total_views', 'unique_views', 'last_viewed_at', 'first_viewed_at'])

                except Exception as e:
                    logger.error(
                        f"Error updating page statistics for content_type {content_type_id} object {object_id}: {e}"
                    )

    # Delete processed keys from Redis
    if keys:
        try:
            redis_client.delete(*keys)
        except Exception as e:
            logger.error(f"Error deleting processed keys from Redis: {e}")

    return processed_count


def generate_daily_summaries(days_back=None):
    """
    Generate daily page view summaries from detailed logs.

    Args:
        days_back (int): Number of days back to process

    Returns:
        int: Number of summaries generated
    """
    days_back = days_back or djinsight_settings.SUMMARY_DAYS_BACK
    logger.info(f"Generating daily summaries for the last {days_back} days")

    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days_back)

    summaries_created = 0

    page_views = (
        PageViewEvent.objects.filter(
            timestamp__date__gte=start_date, timestamp__date__lte=end_date
        )
        .values("content_type", "object_id", "timestamp__date")
        .distinct()
    )

    for view_data in page_views:
        content_type_id = view_data["content_type"]
        content_type = ContentType.objects.get(pk=content_type_id)
        object_id = view_data["object_id"]
        date = view_data["timestamp__date"]

        date_views = PageViewEvent.objects.filter(
            content_type=content_type,
            object_id=object_id,
            timestamp__date=date
        )

        total_views = date_views.count()
        unique_views = date_views.values("session_key").distinct().count()

        summary, created = PageViewSummary.objects.update_or_create(
            content_type=content_type,
            object_id=object_id,
            date=date,
            defaults={
                "total_views": total_views,
                "unique_views": unique_views,
            },
        )

        if created:
            summaries_created += 1

    logger.info(f"Generated {summaries_created} daily summaries")
    return summaries_created


def cleanup_old_data(days_to_keep=None):
    """
    Cleanup old page view logs older than specified days.

    Args:
        days_to_keep (int): Number of days of logs to keep

    Returns:
        int: Number of records deleted
    """
    days_to_keep = days_to_keep or djinsight_settings.CLEANUP_DAYS_TO_KEEP
    cutoff_date = timezone.now() - timedelta(days=days_to_keep)

    logger.info(f"Cleaning up page view logs older than {cutoff_date}")

    deleted_count, _ = PageViewEvent.objects.filter(timestamp__lt=cutoff_date).delete()

    logger.info(f"Deleted {deleted_count} old page view events")

    # Also cleanup old Redis session keys (this is optional)
    if redis_client:
        try:
            # Clean up session keys older than days_to_keep
            session_pattern = f"{REDIS_KEY_PREFIX}session:*"
            session_keys = redis_client.keys(session_pattern)

            # Check TTL and delete expired keys manually
            # (Redis should handle this automatically, but just in case)
            deleted_sessions = 0
            for key in session_keys:
                ttl = redis_client.ttl(key)
                if ttl == -1:  # Key exists but has no expiration
                    redis_client.delete(key)
                    deleted_sessions += 1

            if deleted_sessions > 0:
                logger.info(
                    f"Cleaned up {deleted_sessions} orphaned session keys from Redis"
                )

        except Exception as e:
            logger.error(f"Error cleaning up Redis session keys: {e}")

    return deleted_count


def run_process_page_views(verbosity=1, **options):
    """Function that can be called from management command"""
    batch_size = options.get("batch_size") or djinsight_settings.PROCESS_BATCH_SIZE
    max_records = options.get("max_records") or djinsight_settings.PROCESS_MAX_RECORDS

    if verbosity >= 1:
        print(
            f"Processing page views with batch_size={batch_size}, max_records={max_records}"
        )

    processed = process_page_views(batch_size, max_records)

    if verbosity >= 1:
        print(f"Processed {processed} page views")

    return processed


def run_generate_summaries(verbosity=1, **options):
    """Function that can be called from management command"""
    days_back = options.get("days_back") or djinsight_settings.SUMMARY_DAYS_BACK

    if verbosity >= 1:
        print(f"Generating daily summaries for the last {days_back} days")

    generated = generate_daily_summaries(days_back)

    if verbosity >= 1:
        print(f"Generated {generated} daily summaries")

    return generated


def run_cleanup_old_data(verbosity=1, **options):
    """Function that can be called from management command"""
    days_to_keep = options.get("days_to_keep") or djinsight_settings.CLEANUP_DAYS_TO_KEEP

    if verbosity >= 1:
        print(f"Cleaning up data older than {days_to_keep} days")

    deleted = cleanup_old_data(days_to_keep)

    if verbosity >= 1:
        print(f"Deleted {deleted} old records")

    return deleted
