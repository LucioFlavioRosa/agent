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
            mongo_uri = settings.MONGODB_URI
            db_name = settings.MONGODB_DATABASE_NAME
            if not mongo_uri or not db_name:
                raise ValueError("MONGODB_URI ou MONGODB_DATABASE_NAME não configurados.")
            client = AsyncIOMotorClient(mongo_uri)
            db = client[db_name]
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
            host = settings.REDIS_HOST
            port = settings.REDIS_PORT
            password = settings.REDIS_PASSWORD
            db = settings.REDIS_DB
            use_ssl = settings.REDIS_USE_SSL
            ssl_cert_reqs = settings.REDIS_SSL_CERT_REQS
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
