import redis
import json
from typing import Optional
from domain/models/incremental_change_models import TaskExecutionContext

class ContextCacheService:
    def __init__(self, redis_url: str):
        self.redis = redis.Redis.from_url(redis_url)

    def cache_file_content(self, file_path: str, content: str, ttl: int = 3600):
        key = f"context_cache:{file_path}"
        self.redis.setex(key, ttl, content)

    def get_cached_file(self, file_path: str) -> Optional[str]:
        key = f"context_cache:{file_path}"
        value = self.redis.get(key)
        if value:
            return value.decode()
        return None

    def cache_task_context(self, task_id: str, context: TaskExecutionContext):
        key = f"context_cache:task:{task_id}"
        self.redis.set(key, context.json())

    def get_cached_task_context(self, task_id: str) -> Optional[TaskExecutionContext]:
        key = f"context_cache:task:{task_id}"
        value = self.redis.get(key)
        if value:
            return TaskExecutionContext.parse_raw(value)
        return None

    def invalidate_file_cache(self, file_path: str):
        key = f"context_cache:{file_path}"
        self.redis.delete(key)

    def clear_job_cache(self, job_id: str):
        pattern = f"context_cache:{job_id}:*"
        for key in self.redis.scan_iter(pattern):
            self.redis.delete(key)
