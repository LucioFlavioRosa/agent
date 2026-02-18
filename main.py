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
from backend.app.api.session import router as session_router
from backend.app.api.webhooks import router as webhooks_router
from backend.app.api.user_projects import router as user_projects_router
from backend.app.services.mongodb_service import MongoDBService
from backend.app.api.project_actions import router as project_actions_router
from backend.app.api.groups import router as groups_router
from backend.app.api.user_agents import router as user_agents_router
from backend.app.api.project_management import router as project_management_router

load_dotenv(override=False)

# Silencia logs barulhentos do Azure
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logging.getLogger("azure.monitor.opentelemetry.exporter").setLevel(logging.WARNING)

# --- CONFIGURAÇÃO DE LOGGING (Movida para escopo global) ---
def setup_logging():
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Limpa handlers existentes para evitar duplicação
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    class JsonFormatter(logging.Formatter):
        def format(self, record):
            # 1. Campos Base do Log
            log_record = {
                "timestamp": self.formatTime(record, self.datefmt),
                "level": record.levelname,
                "msg": record.getMessage(),
                "func": record.funcName,
                "module": record.module
            }

            # 2. Mesclagem de Campos Extras
            standard_attribs = {
                'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
                'funcName', 'levelname', 'levelno', 'lineno', 'module',
                'msecs', 'message', 'msg', 'name', 'pathname', 'process',
                'processName', 'relativeCreated', 'stack_info', 'thread', 'threadName'
            }

            # Tudo que vier no 'extra' do logging_utils estará em record.__dict__
            for key, value in record.__dict__.items():
                if key not in standard_attribs:
                    log_record[key] = value

            # 3. Tratamento de Exception (Stack Trace)
            if record.exc_info:
                # Formata a stack trace como string se houver erro
                log_record["exception_trace"] = self.formatException(record.exc_info)

            return json.dumps(log_record)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)
    
setup_logging()

# --- FIM DA CONFIGURAÇÃO DE LOGGING ---
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
app.include_router(session_router, prefix="/session")
app.include_router(webhooks_router, prefix="/webhooks")
app.include_router(user_projects_router, prefix="/user")
app.include_router(project_management_router, prefix="/projects", tags=["Project Management"])
app.include_router(project_actions_router, prefix="/projects", tags=["Project Actions"])
app.include_router(groups_router, prefix="/groups", tags=["Groups"])
app.include_router(user_agents_router, prefix="/user", tags=["User Agents"])

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # Logs estruturados manuais para exceptions
    extra = {"path": request.url.path, "status_code": exc.status_code}
    logging.info(f"[HTTPException] {exc.detail}", extra=extra)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # O exc_info=True fará o formatter adicionar o campo "exception_trace" automaticamente
    extra = {"path": request.url.path, "method": request.method}
    logging.error(f"[UnhandledException] Erro interno: {exc}", exc_info=True, extra=extra)
    return JSONResponse(status_code=500, content={"detail": "Erro interno do servidor."})

@app.on_event("startup")
async def on_startup():
    # setup_logging()  <-- REMOVIDO DAQUI (Já foi chamado no global)
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
        
        logging.info("[Startup] Verificando índices do MongoDB...")
        await mongo_service.create_indexes()
        
        logging.info("[Startup] MongoDBService e índices configurados com sucesso.")
    except Exception as e:
        logging.critical(f"[Startup] Erro crítico no MongoDB: {str(e)}")
        raise

    logging.info("[Startup] Aplicação pronta para receber requisições.")
