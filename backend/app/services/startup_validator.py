import logging
from backend.app.services.mongodb_service import MongoDBService
from backend.app.services.redis_session_service import RedisSessionService

class StartupValidator:
    def __init__(self):
        self.status_report = {}
        self.logger = logging.getLogger("StartupValidator")

    def validate_mongodb_connection(self):
        try:
            mongo_service = MongoDBService()
            # Executa comando de ping para validar conexão
            result = mongo_service.db.command("ping")
            if result.get("ok") == 1.0:
                self.status_report['mongodb'] = {
                    'status': 'ok',
                    'detail': 'Conexão com MongoDB validada via instanciação de MongoDBService e comando de ping.'
                }
            else:
                self.status_report['mongodb'] = {
                    'status': 'fail',
                    'detail': 'Falha ao conectar ao MongoDB: comando de ping não retornou ok.'
                }
        except Exception as e:
            self.status_report['mongodb'] = {
                'status': 'fail',
                'detail': f'Erro ao inicializar MongoDBService ou executar ping: {e}'
            }
            self.logger.error(f"MongoDB validation failed: {e}")

    def validate_redis_connection(self):
        try:
            redis_service = RedisSessionService()
            client = redis_service.redis_client
            client.ping()
            self.status_report['redis'] = {
                'status': 'ok',
                'detail': 'Conexão com Redis validada via instanciação de RedisSessionService e comando de ping.'
            }
        except Exception as e:
            self.status_report['redis'] = {
                'status': 'fail',
                'detail': f'Erro ao inicializar RedisSessionService ou executar ping: {e}'
            }
            self.logger.error(f"Redis connection validation failed: {e}")

    def validate_all_configs(self):
        self.status_report = {}
        self.validate_mongodb_connection()
        self.validate_redis_connection()
        return self.status_report
