# backend/app/main.py
import os
import logging
import json

from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.services.config_loader_service import ConfigLoaderService
from backend.app.core.config import settings

# Importando as rotas separadas
from backend.app.api.auth import router as auth_router
from backend.app.api.upload import router as upload_router

app = FastAPI(
    title="Peers CodeAI Backend", 
    description="Backend para orquestração de Agentes AI e Azure", 
    version="1.0.0"
)

# Configuração de CORS (Lembre-se de restringir em produção)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Em PROD, troque para ["https://seu-frontend.azurewebsites.net"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(auth_router, prefix="/auth")
app.include_router(upload_router, prefix="/upload")

# --- HANDLERS DE ERRO GLOBAIS ---
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Logar o erro real aqui seria uma boa prática (print(exc) ou logger.error(exc))
    logging.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor."}
    )

# --- LOGGING GLOBAL E EVENTO DE STARTUP ---
def setup_logging():
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_file = os.environ.get("LOG_FILE", "backend_app.log")
    logger = logging.getLogger()
    logger.setLevel(log_level)
    # Remove handlers duplicados em reload
    if logger.hasHandlers():
        logger.handlers.clear()
    # Rotating file handler
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)
    # JSON formatter
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            log_record = {
                "timestamp": self.formatTime(record, self.datefmt),
                "level": record.levelname,
                "name": record.name,
                "message": record.getMessage(),
                "pathname": record.pathname,
                "lineno": record.lineno,
                "funcName": record.funcName
            }
            if record.exc_info:
                log_record["exception"] = self.formatException(record.exc_info)
            return json.dumps(log_record)
    file_handler.setFormatter(JsonFormatter())
    logger.addHandler(file_handler)
    # Console handler (também em JSON)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JsonFormatter())
    logger.addHandler(console_handler)

@app.on_event("startup")
def on_startup():
    setup_logging()
    logging.info("Evento de startup iniciado. Carregando segredos do Key Vault...")
    try:
        ConfigLoaderService().load_secrets_from_key_vault()
        # Validação crítica do segredo do Blob Storage
        conn_string = getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", None)
        if not conn_string or not isinstance(conn_string, str) or not conn_string.strip():
            logging.critical("AZURE_STORAGE_CONNECTION_STRING não carregado. Impedindo inicialização do servidor.")
            raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING não carregado do Key Vault ou variável de ambiente. Inicialização abortada.")
        logging.info("Segredos carregados e validados com sucesso.")
    except Exception as e:
        # Bloco try-except mais robusto para erros de nomenclatura de segredos
        error_message = str(e)
        if "not found" in error_message or "404" in error_message or "Segredo" in error_message:
            logging.critical(f"Falha ao carregar segredos do Key Vault: {error_message}")
            logging.critical("Verifique se os nomes dos segredos no Azure Key Vault estão usando hífens (-) ao invés de underscores (_), conforme exigido pela plataforma.")
        else:
            logging.critical(f"Falha ao carregar segredos do Key Vault: {error_message}")
        raise RuntimeError(f"Falha crítica na inicialização: {error_message}")
