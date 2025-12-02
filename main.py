import os
import logging
import json

from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.services.config_loader_service import ConfigLoaderService
from backend.app.core.config import settings

# --- IMPORTAÇÃO DAS ROTAS ---
# É aqui que o main "aprende" a fazer as tarefas.
# Ele delega as funções para os arquivos específicos.
from backend.app.api.auth import router as auth_router
from backend.app.api.upload import router as upload_router
from backend.app.api.analysis import router as analysis_router

# Import necessário para enganar a autenticação durante os testes
from backend.app.middleware.auth_middleware import get_current_user

app = FastAPI(
    title="Peers CodeAI Backend", 
    description="Backend para orquestração de Agentes AI e Azure", 
    version="1.0.0"
)

SKIP_AUTH_FOR_TESTING = True  # <--- Mude para False quando for para Produção real

if SKIP_AUTH_FOR_TESTING:
    async def mock_get_current_user():
        """Retorna um usuário fake para ignorar a validação de token."""
        return {
            "sub": "user-teste-id-123",
            "usuario_executor": "dev_tester_local", # Pasta que será criada no Blob
            "name": "Desenvolvedor Teste",
            "email": "dev@peers.com.br",
            "roles": ["admin"]
        }
    
    # Esta linha mágica substitui a segurança real pelo mock em TODAS as rotas
    app.dependency_overrides[get_current_user] = mock_get_current_user
    logging.warning("⚠️ ALERTA: MODO DE TESTE ATIVO. Autenticação desabilitada.")

# Lista base de IPs locais que devem sempre ser permitidos para o funcionamento interno
ALLOWED_IPS = ["127.0.0.1", "localhost", "::1"]

# Carrega IPs adicionais da variável de ambiente (separados por vírgula)
# Configure no Azure ou .env: ALLOWED_IPS="177.104.212.42,200.100.50.25"
env_ips_str = os.environ.get("ALLOWED_IPS", "")
if env_ips_str:
    extra_ips = [ip.strip() for ip in env_ips_str.split(",") if ip.strip()]
    ALLOWED_IPS.extend(extra_ips)
    logging.info(f"IPs adicionais permitidos via variável de ambiente: {extra_ips}")

@app.middleware("http")
async def ip_restriction_middleware(request: Request, call_next):
    client_ip = request.client.host
    
    # Se estiver rodando no Azure App Service, o IP real vem no header X-Forwarded-For
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    # Se quiser testar livremente, comente o bloco if abaixo
    if client_ip not in ALLOWED_IPS:
        # Se for endpoint de documentação, libera para você ver se o server subiu
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
    allow_origins=["*"], # Permite seu localhost chamar o Azure
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# REGISTRO DE ROTAS
app.include_router(auth_router, prefix="/auth")
app.include_router(upload_router, prefix="/upload")
app.include_router(analysis_router, prefix="/analysis")

# HANDLERS DE ERRO
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logging.error(f"Erro não tratado: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Erro interno do servidor."})

# LOGGING E STARTUP
def setup_logging():
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logger = logging.getLogger()
    logger.setLevel(log_level)
    if logger.hasHandlers(): logger.handlers.clear()
    
    # Formato JSON para Logs (Melhor para Azure Monitor)
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
        # Tenta carregar segredos, mas não crasha se falhar no ambiente de teste local
        ConfigLoaderService().load_secrets_from_key_vault()
        conn_string = getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", None)
        
        if not conn_string:
            logging.warning("⚠️ AZURE_STORAGE_CONNECTION_STRING não encontrado. O Upload vai falhar se tentado.")
        else:
            logging.info("✅ Segredos carregados com sucesso.")
            
    except Exception as e:
        logging.error(f"⚠️ Aviso de Startup (não crítico para teste local): {str(e)}")
