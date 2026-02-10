import logging
import os
from backend.app.core.config import settings
import redis
from motor.motor_asyncio import AsyncIOMotorClient

class StartupValidator:
    def __init__(self):
        self.status_report = {}
        self.logger = logging.getLogger("StartupValidator")

    def validate_mongodb_connection(self):
        try:
            mongo_uri = getattr(settings, "MONGODB_URI", None)
            db_name = getattr(settings, "MONGODB_DATABASE_NAME", None)
            if not mongo_uri or not db_name:
                raise ValueError("MONGODB_URI ou MONGODB_DATABASE_NAME não configurados.")
            client = AsyncIOMotorClient(mongo_uri)
            db = client[db_name]
            # Testa conexão e consulta simples
            result = db.command("ping")
            if result.get("ok") == 1.0:
                self.status_report['mongodb'] = {
                    'status': 'ok',
                    'detail': 'Conexão com MongoDB bem-sucedida.'
                }
            else:
                self.status_report['mongodb'] = {
                    'status': 'fail',
                    'detail': 'Falha ao conectar ao MongoDB.'
                }
        except Exception as e:
            self.status_report['mongodb'] = {
                'status': 'fail',
                'detail': f'Erro ao conectar ao MongoDB: {e}'
            }
            self.logger.error(f"MongoDB validation failed: {e}")

    def validate_redis_connection(self):
        try:
            host = getattr(settings, 'REDIS_HOST', None)
            port = getattr(settings, 'REDIS_PORT', None)
            password = getattr(settings, 'REDIS_PASSWORD', None)
            db = getattr(settings, 'REDIS_DB', None)
            use_ssl = getattr(settings, 'REDIS_USE_SSL', None)
            ssl_cert_reqs = getattr(settings, 'REDIS_SSL_CERT_REQS', None)
            missing = []
            if not host:
                missing.append('REDIS_HOST')
            if not port:
                missing.append('REDIS_PORT')
            if not password:
                missing.append('REDIS_PASSWORD')
            if db is None:
                missing.append('REDIS_DB')
            if use_ssl is None:
                missing.append('REDIS_USE_SSL')
            if ssl_cert_reqs is None:
                missing.append('REDIS_SSL_CERT_REQS')
            if missing:
                self.status_report['redis'] = {
                    'status': 'fail',
                    'detail': f"Segredos do Redis não carregados: {', '.join(missing)}"
                }
                self.logger.error(f"Redis secrets missing: {missing}")
                return
            client = redis.Redis(
                host=host,
                port=int(port),
                password=password,
                db=int(db),
                ssl=use_ssl,
                ssl_cert_reqs=ssl_cert_reqs,
                socket_connect_timeout=5,
                socket_timeout=5,
                decode_responses=True
            )
            client.ping()
            self.status_report['redis'] = {
                'status': 'ok',
                'detail': 'Conexão com Redis via endpoint privado e SSL bem-sucedida.'
            }
        except Exception as e:
            self.status_report['redis'] = {
                'status': 'fail',
                'detail': f'Erro ao conectar ao Redis: {e}'
            }
            self.logger.error(f"Redis connection validation failed: {e}")

    def validate_all_configs(self):
        self.status_report = {}
        self.validate_mongodb_connection()
        self.validate_redis_connection()
        return self.status_report
