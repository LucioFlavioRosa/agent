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
from backend.app.api.groups import router as groups_router
from backend.app.api.user_agents import router as user_agents_router

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
app.include_router(groups_router, prefix="/groups", tags=["Groups"])
app.include_router(user_agents_router, prefix="/user", tags=["User Agents"])

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
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Limpa handlers anteriores
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            # 1. Campos base
            log_record = {
                "timestamp": self.formatTime(record, self.datefmt),
                "level": record.levelname,
                "msg": record.getMessage(),
                "func": record.funcName,
                "module": record.module, # Útil para saber de onde veio
            }
            
            # 2. O PULO DO GATO: Se vierem campos no 'extra', adicione-os ao JSON raiz
            # Campos padrão do LogRecord que queremos ignorar para não poluir
            ignore_keys = {
                'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
                'funcName', 'levelname', 'levelno', 'lineno', 'module',
                'msecs', 'message', 'msg', 'name', 'pathname', 'process',
                'processName', 'relativeCreated', 'stack_info', 'thread', 'threadName'
            }
            
            # Itera sobre o __dict__ do record para pegar o que veio no 'extra'
            for key, value in record.__dict__.items():
                if key not in ignore_keys:
                    log_record[key] = value
            
            # Tratamento de exceção se houver
            if record.exc_info:
                log_record["exception"] = self.formatException(record.exc_info)

            return json.dumps(log_record)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)

@app.on_event("startup")
async def on_startup():  # Mudamos para async
    setup_logging()
    logging.info("🚀 Iniciando Backend Peers CodeAI...")
    logging.info("[Startup] Iniciando carregamento de segredos do Key Vault...")
    
    # 1. Carrega segredos do Key Vault
    try:
        ConfigLoaderService().load_secrets_from_key_vault()
        logging.info("[Startup] ConfigLoaderService: Segredos carregados com sucesso.")
    except Exception as e:
        logging.error(f"⚠️ [Startup] Falha ao carregar segredos: {str(e)}")
        raise RuntimeError(f"Falha ao carregar segredos: {str(e)}")

    # 2. Inicializa MongoDBService e cria Índices
    try:
        logging.info("[Startup] Inicializando MongoDBService...")
        mongo_service = MongoDBService()
        app.state.mongo_service = mongo_service
        
        # AQUI A MUDANÇA: Garante que os índices existam antes da API subir
        logging.info("[Startup] Verificando índices do MongoDB...")
        await mongo_service.create_indexes()
        
        logging.info("[Startup] MongoDBService e índices configurados com sucesso.")
    except Exception as e:
        logging.critical(f"[Startup] Erro crítico no MongoDB: {str(e)}")
        raise

    logging.info("[Startup] Aplicação pronta para receber requisições.")
