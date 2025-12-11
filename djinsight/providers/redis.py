import json
import logging
from typing import Any, Dict

import redis
import redis.asyncio as aioredis
from django.conf import settings
from redis.exceptions import ConnectionError, TimeoutError

from djinsight.conf import djinsight_settings
from djinsight.providers.base import AsyncBaseProvider, BaseProvider

logger = logging.getLogger(__name__)


class RedisProvider(BaseProvider):

    def __init__(self):
        self.client = self._get_redis_client()
        self.key_prefix = djinsight_settings.REDIS_KEY_PREFIX

    def _get_redis_client(self):
        try:
            client = redis.Redis(
                host=djinsight_settings.REDIS_HOST,
                port=djinsight_settings.REDIS_PORT,
                db=djinsight_settings.REDIS_DB,
                password=djinsight_settings.REDIS_PASSWORD,
                socket_timeout=djinsight_settings.REDIS_TIMEOUT,
                socket_connect_timeout=djinsight_settings.REDIS_CONNECT_TIMEOUT,
                health_check_interval=30,
            )
            client.ping()
            logger.info("Redis connection established")
            return client
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Redis connection failed: {e}")
            return None

    def record_view(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.client:
            return {'status': 'error', 'message': 'Redis unavailable'}

        try:
            view_id = event_data['view_id']
            content_type = event_data['content_type']
            object_id = event_data['object_id']
            session_key = event_data['session_key']
            is_unique = event_data['is_unique']

            expiration = djinsight_settings.REDIS_EXPIRATION

            pipe = self.client.pipeline()
            pipe.setex(f"{self.key_prefix}{view_id}", expiration, json.dumps(event_data))
            pipe.incr(f"{self.key_prefix}counter:{content_type}:{object_id}")

            # Always mark session as viewed to prevent counting same session as unique again
            session_key_redis = f"{self.key_prefix}session:{session_key}:page:{content_type}:{object_id}"
            pipe.setex(session_key_redis, expiration, 1)

            # Only increment unique counter if this is first view from this session
            if is_unique:
                pipe.incr(f"{self.key_prefix}unique_counter:{content_type}:{object_id}")

            pipe.execute()

            return {'status': 'success', 'view_id': view_id, 'is_unique': is_unique}

        except Exception as e:
            logger.error(f"Error recording view in Redis: {e}")
            return {'status': 'error', 'message': str(e)}

    def get_stats(self, content_type: str, object_id: int) -> Dict[str, Any]:
        if not self.client:
            return {'total_views': 0, 'unique_views': 0}

        try:
            total_views = self.client.get(f"{self.key_prefix}counter:{content_type}:{object_id}")
            unique_views = self.client.get(f"{self.key_prefix}unique_counter:{content_type}:{object_id}")

            return {
                'total_views': int(total_views) if total_views else 0,
                'unique_views': int(unique_views) if unique_views else 0,
            }
        except Exception as e:
            logger.error(f"Error getting stats from Redis: {e}")
            return {'total_views': 0, 'unique_views': 0}

    def increment_counter(self, key: str, amount: int = 1) -> int:
        if not self.client:
            return 0

        try:
            return self.client.incr(f"{self.key_prefix}{key}", amount)
        except Exception as e:
            logger.error(f"Error incrementing counter: {e}")
            return 0

    def check_unique_view(self, session_key: str, content_type: str, object_id: int) -> bool:
        if not self.client:
            return False

        try:
            key = f"{self.key_prefix}session:{session_key}:page:{content_type}:{object_id}"
            return not self.client.exists(key)
        except Exception as e:
            logger.error(f"Error checking unique view: {e}")
            return False

    def mark_viewed(self, session_key: str, content_type: str, object_id: int, ttl: int) -> None:
        if not self.client:
            return

        try:
            key = f"{self.key_prefix}session:{session_key}:page:{content_type}:{object_id}"
            self.client.setex(key, ttl, 1)
        except Exception as e:
            logger.error(f"Error marking viewed: {e}")


class AsyncRedisProvider(AsyncBaseProvider):
    """Async Redis provider for use with async Django views."""

    def __init__(self):
        self.client = None
        self.key_prefix = djinsight_settings.REDIS_KEY_PREFIX
        self._initialized = False

    async def _get_redis_client(self):
        """Get or create async Redis client."""
        if self.client is None:
            try:
                self.client = aioredis.Redis(
                    host=djinsight_settings.REDIS_HOST,
                    port=djinsight_settings.REDIS_PORT,
                    db=djinsight_settings.REDIS_DB,
                    password=djinsight_settings.REDIS_PASSWORD,
                    socket_timeout=djinsight_settings.REDIS_TIMEOUT,
                    socket_connect_timeout=djinsight_settings.REDIS_CONNECT_TIMEOUT,
                )
                await self.client.ping()
                logger.info("Async Redis connection established")
                self._initialized = True
            except (ConnectionError, TimeoutError) as e:
                logger.error(f"Async Redis connection failed: {e}")
                self.client = None
        return self.client

    async def record_view(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        client = await self._get_redis_client()
        if not client:
            return {'status': 'error', 'message': 'Redis unavailable'}

        try:
            view_id = event_data['view_id']
            content_type = event_data['content_type']
            object_id = event_data['object_id']
            session_key = event_data['session_key']
            is_unique = event_data['is_unique']

            expiration = djinsight_settings.REDIS_EXPIRATION

            pipe = client.pipeline()
            pipe.setex(f"{self.key_prefix}{view_id}", expiration, json.dumps(event_data))
            pipe.incr(f"{self.key_prefix}counter:{content_type}:{object_id}")

            # Always mark session as viewed to prevent counting same session as unique again
            session_key_redis = f"{self.key_prefix}session:{session_key}:page:{content_type}:{object_id}"
            pipe.setex(session_key_redis, expiration, 1)

            # Only increment unique counter if this is first view from this session
            if is_unique:
                pipe.incr(f"{self.key_prefix}unique_counter:{content_type}:{object_id}")

            await pipe.execute()

            return {'status': 'success', 'view_id': view_id, 'is_unique': is_unique}

        except Exception as e:
            logger.error(f"Error recording view in async Redis: {e}")
            return {'status': 'error', 'message': str(e)}

    async def get_stats(self, content_type: str, object_id: int) -> Dict[str, Any]:
        client = await self._get_redis_client()
        if not client:
            return {'total_views': 0, 'unique_views': 0}

        try:
            total_views = await client.get(f"{self.key_prefix}counter:{content_type}:{object_id}")
            unique_views = await client.get(f"{self.key_prefix}unique_counter:{content_type}:{object_id}")

            return {
                'total_views': int(total_views) if total_views else 0,
                'unique_views': int(unique_views) if unique_views else 0,
            }
        except Exception as e:
            logger.error(f"Error getting stats from async Redis: {e}")
            return {'total_views': 0, 'unique_views': 0}

    async def increment_counter(self, key: str, amount: int = 1) -> int:
        client = await self._get_redis_client()
        if not client:
            return 0

        try:
            return await client.incr(f"{self.key_prefix}{key}", amount)
        except Exception as e:
            logger.error(f"Error incrementing counter: {e}")
            return 0

    async def check_unique_view(self, session_key: str, content_type: str, object_id: int) -> bool:
        client = await self._get_redis_client()
        if not client:
            return False

        try:
            key = f"{self.key_prefix}session:{session_key}:page:{content_type}:{object_id}"
            return not await client.exists(key)
        except Exception as e:
            logger.error(f"Error checking unique view: {e}")
            return False

    async def mark_viewed(self, session_key: str, content_type: str, object_id: int, ttl: int) -> None:
        client = await self._get_redis_client()
        if not client:
            return

        try:
            key = f"{self.key_prefix}session:{session_key}:page:{content_type}:{object_id}"
            await client.setex(key, ttl, 1)
        except Exception as e:
            logger.error(f"Error marking viewed: {e}")

    async def close(self):
        """Close async Redis connection."""
        if self.client:
            await self.client.close()
