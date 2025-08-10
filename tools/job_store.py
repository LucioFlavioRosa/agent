# Arquivo: job_store.py
import redis
import os
import json
from typing import Optional, Dict

# Pega a URL de conexão do Redis das variáveis de ambiente
REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    raise ValueError("A variável de ambiente REDIS_URL não foi configurada.")

# Inicializa o cliente Redis
# O decode_responses=True faz com que os resultados venham como strings, não bytes
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

def set_job(job_id: str, job_data: Dict):
    """ Salva os dados de um job no Redis, convertendo para JSON. """
    # Define um tempo de expiração de 24 horas para os jobs não ficarem para sempre
    # O tempo é em segundos: 60 seg * 60 min * 24 horas = 86400
    redis_client.set(job_id, json.dumps(job_data), ex=86400)

def get_job(job_id: str) -> Optional[Dict]:
    """ Pega os dados de um job do Redis, convertendo de JSON para dicionário. """
    job_json = redis_client.get(job_id)
    if job_json:
        return json.loads(job_json)
    return None
