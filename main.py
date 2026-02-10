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
from backend.app.services.startup_validator import StartupValidator
#from backend.app.api.auth import router as auth_router
from backend.app.api.analysis import router as analysis_router
from backend.app.api.projects import router as projects_router
from backend.app.api.session import router as session_router
from backend.app.api.webhooks import router as webhooks_router

load_dotenv(override=False)

logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logging.getLogger("azure.monitor.opentelemetry.exporter").setLevel(logging.WARNING)

app = FastAPI(
    title="Peers CodeAI Backend", 
    description="Backend para orquestração de Agentes AI e Azure", 
    version="1.0.0"
)

# Removido SKIP_AUTH_FOR_TESTING e get_current_user: autenticação agora é feita pelo frontend

# IP Restriction Middleware permanece para segurança de infraestrutura

def _extract_client_ip(request: Request) -> str:
    client_ip = request.client.host
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    if ":" in client_ip and "." in client_ip:
        client_ip = client_ip.split(":")[0]
    return client_ip

ALLOWED_IPS = ["127.0.0.1", "localhost", "::1"]
env_ips_str = os.environ.get("ALLOWED_IPS", "")
if env_ips_str:
    extra_ips = [ip.strip() for ip in env_ips_str.split(",") if ip.strip()]
    ALLOWED_IPS.extend(extra_ips)
    logging.info(f"IPs adicionais permitidos: {extra_ips}")

@app.middleware("http")
async def ip_restriction_middleware(request: Request, call_next):
    client_ip = _extract_client_ip(request)
    if "*" not in ALLOWED_IPS and client_ip not in ALLOWED_IPS:
        if request.url.path not in ["/docs", "/openapi.json", "/redoc"]:
            logging.warning(f"⛔ Acesso negado: IP {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": f"Acesso negado. IP {client_ip} não autorizado."}
            )
    response = await call_next(request)
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(analysis_router, prefix="/analysis")
app.include_router(projects_router, prefix="/projects")
app.include_router(session_router, prefix="/session")
app.include_router(webhooks_router, prefix="/webhooks")

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
    setup_logging()
    logging.info("🚀 Iniciando Backend Peers CodeAI...")
    try:
        # Carregar apenas segredos do Redis, não Azure AD ou Blob Storage
        ConfigLoaderService().load_secrets_from_key_vault()
        # Removido: validação de AZURE_STORAGE_CONNECTION_STRING
        validator = StartupValidator()
        validator.validate_redis_connection()
        if validator.status_report.get('redis', {}).get('status') != 'ok':
            logging.critical(f"Erro crítico Redis: {validator.status_report['redis']['detail']}")
    except Exception as e:
        logging.error(f"⚠️ Aviso de Startup: {str(e)}")
