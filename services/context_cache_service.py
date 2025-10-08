import redis
import json
from typing import Optional
from domain/models/incremental_change_models import TaskExecutionContext

class ContextCacheService:
    def __init__(self, redis_url: str):
        self.redis = redis.Redis.from_url(redis_url)
        self.cache_hits = 0
        self.cache_requests = 0

    def cache_file_content(self, file_path: str, content: str, ttl: int = 3600):
        key = f"context_cache:{file_path}"
        self.redis.setex(key, ttl, content)

    def get_cached_file(self, file_path: str) -> Optional[str]:
        key = f"context_cache:{file_path}"
        self.cache_requests += 1
        value = self.redis.get(key)
        if value:
            self.cache_hits += 1
            return value.decode()
        return None

    def cache_task_context(self, task_id: str, context: TaskExecutionContext, dependency_graph=None):
        key = f"context_cache:task:{task_id}"
        self.redis.set(key, context.json())
        preloaded_files = set()
        if dependency_graph:
            for succ in dependency_graph.adjacency_list.get(task_id, []):
                succ_task = dependency_graph.tasks.get(succ)
                if succ_task:
                    for file_path in succ_task.dependencies:
                        if not self.get_cached_file(file_path):
                            file_content = context.related_files.get(file_path, "")
                            if file_content:
                                self.cache_file_content(file_path, file_content)
                                preloaded_files.add(file_path)
            print(f"Pré-carregados {len(preloaded_files)} arquivos para tarefas futuras")
        total_requests = self.cache_requests if self.cache_requests > 0 else 1
        print(f"Cache hit rate: {self.cache_hits}/{total_requests * 100:.2f}%")

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
