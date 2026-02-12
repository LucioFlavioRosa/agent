import os
import json
import logging
from dotenv import load_dotenv

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.services.config_loader_service import ConfigLoaderService
from backend.app.core.config import settings
from backend.app.api.auth import router as auth_router
from backend.app.api.analysis import router as analysis_router
from backend.app.api.projects import router as projects_router
from backend.app.api.session import router as session_router
from backend.app.api.webhooks import router as webhooks_router
from backend.app.api.user_projects import router as user_projects_router
from backend.app.services.mongodb_service import MongoDBService
from backend.app.api.project_management import router as project_management_router
from backend.app.utils import logger_utils

load_dotenv(override=False)

logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logging.getLogger("azure.monitor.opentelemetry.exporter").setLevel(logging.WARNING)

app = FastAPI(
    title="Peers CodeAI Backend", 
    description="Backend para orquestração de Agentes AI e Azure", 
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

logger_utils.log_service_call(logging.getLogger("main"), "startup", "Registrando routers", {})
app.include_router(auth_router, prefix="/auth")
logger_utils.log_service_call(logging.getLogger("main"), "startup", "Router registrado", {"prefix": "/auth", "tags": getattr(auth_router, 'tags', None)})
app.include_router(analysis_router, prefix="/analysis")
logger_utils.log_service_call(logging.getLogger("main"), "startup", "Router registrado", {"prefix": "/analysis", "tags": getattr(analysis_router, 'tags', None)})
app.include_router(projects_router, prefix="/projects")
logger_utils.log_service_call(logging.getLogger("main"), "startup", "Router registrado", {"prefix": "/projects", "tags": getattr(projects_router, 'tags', None)})
app.include_router(session_router, prefix="/session")
logger_utils.log_service_call(logging.getLogger("main"), "startup", "Router registrado", {"prefix": "/session", "tags": getattr(session_router, 'tags', None)})
app.include_router(webhooks_router, prefix="/webhooks")
logger_utils.log_service_call(logging.getLogger("main"), "startup", "Router registrado", {"prefix": "/webhooks", "tags": getattr(webhooks_router, 'tags', None)})
app.include_router(user_projects_router, prefix="/user")
logger_utils.log_service_call(logging.getLogger("main"), "startup", "Router registrado", {"prefix": "/user", "tags": getattr(user_projects_router, 'tags', None)})
app.include_router(project_management_router, prefix="/projects", tags=["Project Management"])
logger_utils.log_service_call(logging.getLogger("main"), "startup", "Router registrado", {"prefix": "/projects", "tags": ["Project Management"]})

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logging.error(f"Erro não tratado: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Erro interno do servidor."})

def setup_logging():
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logger = logging.getLogger()
    logger.setLevel(log_level)
    if logger.hasHandlers(): logger.handlers.clear()
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            log_record = {
                "timestamp": self.formatTime(record, self.datefmt),
                "level": record.levelname,
                "msg": record.getMessage(),
                "func": record.funcName
            }
            return json.dumps(log_record)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)

@app.on_event("startup")
def on_startup():
    logger_utils.log_service_call(logging.getLogger("main"), "on_startup", "Iniciando aplicação", {})
    setup_logging()
    logging.info("🚀 Iniciando Backend Peers CodeAI...")
    # Carrega segredos do Key Vault (incluindo Redis)
    try:
        logger_utils.log_service_call(logging.getLogger("main"), "on_startup", "Carregando segredos do Key Vault", {})
        ConfigLoaderService().load_secrets_from_key_vault()
        logger_utils.log_response_sent(logging.getLogger("main"), "on_startup", "Segredos carregados do Key Vault com sucesso", {})
        logging.info("ConfigLoaderService: Segredos carregados do Key Vault com sucesso.")
    except Exception as e:
        logger_utils.log_response_sent(logging.getLogger("main"), "on_startup", f"Falha ao carregar segredos do Key Vault: {str(e)}", {})
        logging.error(f"⚠️ Aviso de Startup: {str(e)}")
        raise RuntimeError(f"Falha ao carregar segredos do Key Vault: {str(e)}")
    # Removida validação de settings.MONGODB_URI e settings.MONGODB_DATABASE_NAME
    try:
        logger_utils.log_service_call(logging.getLogger("main"), "on_startup", "Inicializando MongoDBService", {})
        app.state.mongo_service = MongoDBService()
        logger_utils.log_response_sent(logging.getLogger("main"), "on_startup", "MongoDBService inicializado com sucesso", {})
        logging.info("MongoDBService inicializado com sucesso.")
    except Exception as e:
        logger_utils.log_response_sent(logging.getLogger("main"), "on_startup", f"Erro ao inicializar MongoDBService: {str(e)}", {})
        logging.critical(f"Erro ao inicializar MongoDBService: {str(e)}")
        raise
