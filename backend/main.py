# backend/app/main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

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
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor."}
    )
