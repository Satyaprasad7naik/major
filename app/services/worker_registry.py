"""
Worker Registry (Redis)
========================
Stores taskArn for engine and generator workers so the API can:
- Report status: if key present → worker is running
- Stop: fetch taskArn from Redis, stop the task, then remove the key
"""

from typing import Optional
import redis

from app.core.config import settings

# Redis key names for worker task ARNs
REDIS_KEY_ENGINE_TASK_ARN = "alerts:engine:task_arn"
REDIS_KEY_GENERATOR_TASK_ARN = "alerts:generator:task_arn"


class WorkerRegistry:
    """Redis-backed registry for engine and generator worker task ARNs."""

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._client: Optional[redis.Redis] = None
        self._available = False
        self._init_redis()

    def _init_redis(self):
        try:
            self._client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            self._client.ping()
            self._available = True
        except (redis.ConnectionError, redis.TimeoutError):
            self._available = False
            self._client = None

    @property
    def redis(self) -> Optional[redis.Redis]:
        if self._client is None:
            self._init_redis()
        return self._client

    def set_engine_task_arn(self, task_arn: str) -> bool:
        """Store engine worker taskArn in Redis."""
        if not self.redis:
            return False
        try:
            self.redis.set(REDIS_KEY_ENGINE_TASK_ARN, task_arn)
            return True
        except redis.RedisError:
            return False

    def get_engine_task_arn(self) -> Optional[str]:
        """Get engine worker taskArn from Redis. None if not running."""
        if not self.redis:
            return None
        try:
            return self.redis.get(REDIS_KEY_ENGINE_TASK_ARN)
        except redis.RedisError:
            return None

    def delete_engine_task_arn(self) -> bool:
        """Remove engine taskArn from Redis (after stopping the task)."""
        if not self.redis:
            return False
        try:
            self.redis.delete(REDIS_KEY_ENGINE_TASK_ARN)
            return True
        except redis.RedisError:
            return False

    def set_generator_task_arn(self, task_arn: str) -> bool:
        """Store generator worker taskArn in Redis."""
        if not self.redis:
            return False
        try:
            self.redis.set(REDIS_KEY_GENERATOR_TASK_ARN, task_arn)
            return True
        except redis.RedisError:
            return False

    def get_generator_task_arn(self) -> Optional[str]:
        """Get generator worker taskArn from Redis. None if not running."""
        if not self.redis:
            return None
        try:
            return self.redis.get(REDIS_KEY_GENERATOR_TASK_ARN)
        except redis.RedisError:
            return None

    def delete_generator_task_arn(self) -> bool:
        """Remove generator taskArn from Redis (after stopping the task)."""
        if not self.redis:
            return False
        try:
            self.redis.delete(REDIS_KEY_GENERATOR_TASK_ARN)
            return True
        except redis.RedisError:
            return False

    def is_available(self) -> bool:
        return self._available


# Singleton for API use
worker_registry = WorkerRegistry()
