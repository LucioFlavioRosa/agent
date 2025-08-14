# Arquivo: tools/job_store.py (VERSÃO REVISADA E RECOMENDADA)

import redis
import os
import json
from typing import Optional, Dict, Any
from domain.interfaces.job_store_interface import JobStoreInterface

class RedisJobStore(JobStoreInterface):
    """
    Implementação concreta de JobStoreInterface usando Redis.
    """
    def __init__(self):
        REDIS_URL = os.getenv("REDIS_URL")
        if not REDIS_URL:
            raise ValueError("A variável de ambiente REDIS_URL não foi configurada.")
        print(f"Conectando ao Redis via URL: {REDIS_URL.split('@')[-1]}")
        self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        self.JOB_KEY_PREFIX = "mcp_job"

    def set_job(self, job_id: str, job_data: Dict[str, Any], ttl: int = 86400):
        key = f"{self.JOB_KEY_PREFIX}:{job_id}"
        try:
            self.redis_client.set(key, json.dumps(job_data), ex=ttl)
        except redis.exceptions.RedisError as e:
            print(f"ERRO CRÍTICO ao salvar no Redis [Chave: {key}]: {e}")

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        key = f"{self.JOB_KEY_PREFIX}:{job_id}"
        try:
            job_json = self.redis_client.get(key)
            if job_json:
                return json.loads(job_json)
            return None
        except redis.exceptions.RedisError as e:
            print(f"ERRO CRÍTICO ao ler do Redis [Chave: {key}]: {e}")
            return None
