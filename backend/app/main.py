from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_500_INTERNAL_SERVER_ERROR
from backend.app.api.auth import router as auth_router
from backend.app.api.upload import router as upload_router
from backend.app.middleware.auth_middleware import AuthMiddleware

# Instância FastAPI exportável
app = FastAPI(title="Backend API", description="Backend para upload e autenticação JWT", version="1.0.0")

# Configurar CORS para permitir requisições do front-end
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Adicionar middleware de autenticação JWT
app.add_middleware(AuthMiddleware)

# Registrar routers
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(upload_router, prefix="/upload", tags=["upload"])

# Tratamento global de exceções
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Erro interno do servidor."}
    )

@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc):
    return JSONResponse(
        status_code=HTTP_401_UNAUTHORIZED,
        content={"detail": "Token JWT inválido ou ausente."}
    )

# Nenhuma lógica de execução direta (uvicorn.run, if __name__ == "__main__")
# Apenas exporta a instância 'app' para ser usada por backend/main.py
