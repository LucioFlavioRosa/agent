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
from backend.app.api.project_actions import router as project_actions_router

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

app.include_router(auth_router, prefix="/auth")
app.include_router(analysis_router, prefix="/analysis")
app.include_router(projects_router, prefix="/projects")
app.include_router(session_router, prefix="/session")
app.include_router(webhooks_router, prefix="/webhooks")
app.include_router(user_projects_router, prefix="/user")
app.include_router(project_management_router, prefix="/projects", tags=["Project Management"])
app.include_router(project_actions_router, prefix="/projects", tags=["Project Actions"])

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logging.info(f"[HTTPException] {exc.status_code} - {exc.detail} - Path: {request.url.path}")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logging.error(f"[UnhandledException] Erro não tratado: {exc}", exc_info=True)
    logging.error(f"[UnhandledException] Path: {request.url.path}, Method: {request.method}")
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
    setup_logging()
    logging.info("🚀 Iniciando Backend Peers CodeAI...")
    logging.info("[Startup] Iniciando carregamento de segredos do Key Vault...")
    # Carrega segredos do Key Vault (incluindo Redis)
    try:
        ConfigLoaderService().load_secrets_from_key_vault()
        logging.info("[Startup] ConfigLoaderService: Segredos carregados do Key Vault com sucesso.")
    except Exception as e:
        logging.error(f"⚠️ [Startup] Falha ao carregar segredos do Key Vault: {str(e)}")
        raise RuntimeError(f"Falha ao carregar segredos do Key Vault: {str(e)}")
    # Removida validação de settings.MONGODB_URI e settings.MONGODB_DATABASE_NAME
    try:
        logging.info("[Startup] Inicializando MongoDBService...")
        app.state.mongo_service = MongoDBService()
        logging.info("[Startup] MongoDBService inicializado com sucesso.")
    except Exception as e:
        logging.critical(f"[Startup] Erro ao inicializar MongoDBService: {str(e)}")
        raise
    logging.info("[Startup] Aplicação pronta para receber requisições.")
