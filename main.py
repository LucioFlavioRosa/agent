import os
import logging
import json
from dotenv import load_dotenv

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.services.config_loader_service import ConfigLoaderService
from backend.app.core.config import settings
from backend.app.services.startup_validator import StartupValidator

from backend.app.api.auth import router as auth_router
from backend.app.api.analysis import router as analysis_router
from backend.app.api.projects import router as projects_router
from backend.app.api.session import router as session_router
from backend.app.api.webhooks import router as webhooks_router

from backend.app.middleware.auth_middleware import get_current_user

load_dotenv(override=False)

app = FastAPI(
    title="Peers CodeAI Backend", 
    description="Backend para orquestração de Agentes AI e Azure", 
    version="1.0.0"
)

SKIP_AUTH_FOR_TESTING = True

def _create_mock_user(request: Request) -> dict:
    test_user_header = request.headers.get("X-Test-User-Json")
    if test_user_header:
        try:
            user_data = json.loads(test_user_header)
            logging.info(f"🧪 [MOCK AUTH] Usando usuário dinâmico: {user_data.get('email')}")
            return user_data
        except json.JSONDecodeError:
            logging.error("Erro ao decodificar X-Test-User-Json")
    return {
        "sub": "user-teste-id-123",
        "usuario_executor": "dev_tester_local",
        "name": "Desenvolvedor Teste",
        "email": "dev@peers.com.br",
        "roles": ["admin"]
    }

if SKIP_AUTH_FOR_TESTING:
    async def mock_get_current_user(request: Request):
        return _create_mock_user(request)
    app.dependency_overrides[get_current_user] = mock_get_current_user
    logging.warning("⚠️ ALERTA: MODO DE TESTE ATIVO. Autenticação via Header habilitada.")

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

app.include_router(auth_router, prefix="/auth")
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
        ConfigLoaderService().load_secrets_from_key_vault()
        conn_string = getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", None)
        if not conn_string:
            logging.warning("⚠️ AZURE_STORAGE_CONNECTION_STRING não encontrado. O Upload vai falhar se tentado.")
        else:
            logging.info("✅ Segredos carregados com sucesso.")
        validator = StartupValidator()
        validator.validate_redis_connection()
        if validator.status_report.get('redis', {}).get('status') != 'ok':
            logging.critical(f"Erro crítico Redis: {validator.status_report['redis']['detail']}")
    except Exception as e:
        logging.error(f"⚠️ Aviso de Startup: {str(e)}")
