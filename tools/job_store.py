# Arquivo: tools/job_store.py (VERSÃO REVISADA E RECOMENDADA)

import redis
import os
import json
from typing import Optional, Dict, Any
from domain.interfaces.job_store_interface import JobStoreInterface

class RedisJobStore(JobStoreInterface):
    """
    Implementação concreta de JobStoreInterface usando Redis.
    Suporta indexação e busca de jobs por analysis_name.
    """
    def __init__(self):
        REDIS_URL = os.getenv("REDIS_URL")
        if not REDIS_URL:
            raise ValueError("A variável de ambiente REDIS_URL não foi configurada.")
        print(f"Conectando ao Redis via URL: {REDIS_URL.split('@')[-1]}")
        self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        self.JOB_KEY_PREFIX = "mcp_job"
        self.ANALYSIS_NAME_INDEX = "mcp_analysis_name_index"

    def set_job(self, job_id: str, job_data: Dict[str, Any], ttl: int = 86400):
        key = f"{self.JOB_KEY_PREFIX}:{job_id}"
        try:
            self.redis_client.set(key, json.dumps(job_data), ex=ttl)
            # Indexa analysis_name se presente
            analysis_name = job_data.get('data', {}).get('analysis_name')
            if analysis_name:
                self.set_analysis_name_index(job_id, analysis_name)
        except redis.exceptions.RedisError as e:
            print(f"ERRO CRÍTICO ao salvar no Redis [Chave: {key}]: {e}")

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        key = f"{self.JOB_KEY_PREFIX}:{job_id}"
        try:
            job_json = self.redis_client.get(key)
            if job_json:
                job = json.loads(job_json)
                job['job_id'] = job_id
                return job
            return None
        except redis.exceptions.RedisError as e:
            print(f"ERRO CRÍTICO ao ler do Redis [Chave: {key}]: {e}")
            return None

    def set_analysis_name_index(self, job_id: str, analysis_name: str):
        """
        Indexa o analysis_name (normalizado) para o job_id. Usa hash para garantir unicidade.
        """
        try:
            analysis_name_normalized = analysis_name.lower()
            self.redis_client.hset(self.ANALYSIS_NAME_INDEX, analysis_name_normalized, job_id)
        except redis.exceptions.RedisError as e:
            print(f"ERRO ao indexar analysis_name '{analysis_name}': {e}")

    def get_job_by_analysis_name(self, analysis_name: str) -> Optional[Dict[str, Any]]:
        """
        Busca o job pelo analysis_name normalizado.
        """
        try:
            analysis_name_normalized = analysis_name.lower()
            job_id = self.redis_client.hget(self.ANALYSIS_NAME_INDEX, analysis_name_normalized)
            if not job_id:
                return None
            return self.get_job(job_id)
        except redis.exceptions.RedisError as e:
            print(f"ERRO ao buscar job por analysis_name '{analysis_name}': {e}")
            return None
