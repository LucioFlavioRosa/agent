import os
import msal
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form, BackgroundTasks, Depends, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional
from pydantic import BaseModel
from backend.app.core.config import settings
from backend.app.services.blob_storage_service import upload_docx_to_blob
from backend.app.services.docx_parser_service import extract_text_from_docx
from backend.app.services.mcp_client_service import MCPClientService, MCPStartAnalysisPayload
from backend.app.services.azure_ad_service import AzureADService
from backend.app.api.auth import router as auth_router
from backend.app.api.upload import router as upload_router
from backend.app.middleware.auth_middleware import get_current_user

class UploadDocxResponse(BaseModel):
    job_id: str
    blob_url: str
    message: str

azure_ad_service = AzureADService()

app = FastAPI(title="Backend API", description="Backend para upload e autenticação JWT", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Removido: app.add_middleware(AuthMiddleware)

# Registro dos routers (auth e upload)
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(upload_router, prefix="/upload", tags=["upload"])

# ---
# O endpoint POST /auth/login foi removido por segurança.
# O fluxo recomendado agora é: o frontend obtém o token diretamente da Microsoft (MSAL.js) e envia o Bearer token para o backend.
# ---

@app.post("/upload/docx", response_model=UploadDocxResponse, tags=["Upload"])
async def upload_docx(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    projeto: str = Form(...),
    analysis_name: str = Form(...),
    analysis_type: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    usuario_executor = current_user.get("usuario_executor") or current_user.get("sub")
    # Removida validação manual: if not usuario_executor: raise HTTPException(...)
    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Apenas arquivos .docx são permitidos.")
    try:
        texto_extraido = await extract_text_from_docx(file)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao extrair texto do docx: {str(e)}")
    blob_folder = f"{usuario_executor}/{projeto}/arquivos_recebidos/docx"
    blob_filename = f"{analysis_name}.docx"
    blob_url = await upload_docx_to_blob(file, blob_folder, blob_filename, background_tasks)
    payload = MCPStartAnalysisPayload(
        analysis_type=analysis_type,
        instrucoes_extras=texto_extraido,
        projeto=projeto,
        analysis_name=analysis_name,
        usuario_executor=usuario_executor
    )
    mcp_client = MCPClientService()
    try:
        mcp_response = await mcp_client.start_analysis(payload)
        job_id = mcp_response.job_id
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao comunicar com MCP Server: {str(e)}")
    return UploadDocxResponse(job_id=job_id, blob_url=blob_url, message="Arquivo recebido, salvo e análise iniciada com sucesso.")

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor."}
    )

@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc):
    return JSONResponse(
        status_code=401,
        content={"detail": "Token JWT inválido ou ausente."}
    )
