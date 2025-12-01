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

# Importando as rotas (Note a adição do analysis_router)
from backend.app.api.auth import router as auth_router
from backend.app.api.upload import router as upload_router
from backend.app.api.analysis import router as analysis_router

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

# Registrando as rotas
app.include_router(auth_router, prefix="/auth")
app.include_router(upload_router, prefix="/upload")
app.include_router(analysis_router, prefix="/analysis")

# --- HANDLERS DE ERRO GLOBAIS ---
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Logar o erro real aqui
    logging.error(f"Unhandled exception: {exc}", exc_info=True)
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
    
    if logger.hasHandlers():
        logger.handlers.clear()
        
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)
    
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
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JsonFormatter())
    logger.addHandler(console_handler)

@app.on_event("startup")
def on_startup():
    setup_logging()
    logging.info("Evento de startup iniciado. Carregando segredos do Key Vault...")
    try:
        ConfigLoaderService().load_secrets_from_key_vault()
        
        conn_string = getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", None)
        if not conn_string or not isinstance(conn_string, str) or not conn_string.strip():
            logging.critical("AZURE_STORAGE_CONNECTION_STRING não carregado. Impedindo inicialização do servidor.")
            raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING não carregado do Key Vault ou variável de ambiente.")
            
        logging.info("Segredos carregados e validados com sucesso.")
    except Exception as e:
        error_message = str(e)
        if "not found" in error_message or "404" in error_message or "Segredo" in error_message:
            logging.critical(f"Falha ao carregar segredos do Key Vault: {error_message}")
            logging.critical("Verifique se os nomes dos segredos no Azure Key Vault estão usando hífens (-) ao invés de underscores (_).")
        else:
            logging.critical(f"Falha ao carregar segredos do Key Vault: {error_message}")
        raise RuntimeError(f"Falha crítica na inicialização: {error_message}")
