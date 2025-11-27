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

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

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

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth: str = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(auth)
        if not auth or scheme.lower() != "bearer":
            return await call_next(request)
        try:
            user = azure_ad_service.validate_token(param)
            request.state.user = user
        except HTTPException:
            return await call_next(request)
        response = await call_next(request)
        return response

def get_current_user(request: Request):
    auth: str = request.headers.get("Authorization")
    scheme, param = get_authorization_scheme_param(auth)
    if not auth or scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Cabeçalho Authorization ausente ou inválido.")
    return azure_ad_service.validate_token(param)

app.add_middleware(AuthMiddleware)

@app.post("/auth/login", response_model=LoginResponse, tags=["Auth"])
def login(request: LoginRequest):
    AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", settings.AZURE_AD_CLIENT_ID)
    AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID", settings.AZURE_AD_TENANT_ID)
    AZURE_AUTHORITY = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}"
    AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", settings.AZURE_AD_CLIENT_SECRET)
    AZURE_SCOPE = [os.environ.get("AZURE_SCOPE", "User.Read")]
    app_msal = msal.ConfidentialClientApplication(
        AZURE_CLIENT_ID,
        authority=AZURE_AUTHORITY,
        client_credential=AZURE_CLIENT_SECRET
    )
    result = app_msal.acquire_token_by_username_password(
        username=request.username,
        password=request.password,
        scopes=AZURE_SCOPE
    )
    if "access_token" not in result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Falha na autenticação Azure AD: {result.get('error_description', 'Erro desconhecido')}"
        )
    return LoginResponse(
        access_token=result["access_token"],
        expires_in=result.get("expires_in", 3600)
    )

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
    if not usuario_executor:
        raise HTTPException(status_code=401, detail="Usuário não autenticado no token.")
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
