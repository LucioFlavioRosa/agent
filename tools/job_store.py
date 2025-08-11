# Arquivo: tools/job_store.py (VERSÃO REVISADA E RECOMENDADA)

import redis
import os
import json
from typing import Optional, Dict, Any

# Pega a URL de conexão do Redis das variáveis de ambiente
REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    raise ValueError("A variável de ambiente REDIS_URL não foi configurada.")

print(f"Conectando ao Redis via URL: {REDIS_URL.split('@')[-1]}") # Log para confirmação

# Inicializa o cliente Redis a partir da URL
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# [MELHORIA] Adiciona um prefixo para organizar as chaves no Redis
JOB_KEY_PREFIX = "mcp_job"

def set_job(job_id: str, job_data: Dict[str, Any], ttl: int = 86400):
    """ Salva os dados de um job no Redis, convertendo para JSON. """
    key = f"{JOB_KEY_PREFIX}:{job_id}"
    try:
        redis_client.set(key, json.dumps(job_data), ex=ttl) # Expira em 24h por padrão
    except redis.exceptions.RedisError as e:
        print(f"ERRO CRÍTICO ao salvar no Redis [Chave: {key}]: {e}")


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """ Pega os dados de um job do Redis, convertendo de JSON para dicionário. """
    key = f"{JOB_KEY_PREFIX}:{job_id}"
    try:
        job_json = redis_client.get(key)
        if job_json:
            return json.loads(job_json)
        return None
    except redis.exceptions.RedisError as e:
        print(f"ERRO CRÍTICO ao ler do Redis [Chave: {key}]: {e}")
        return None
