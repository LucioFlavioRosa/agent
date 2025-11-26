from fastapi import APIRouter, UploadFile, File, Form, Header, BackgroundTasks, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from typing import Optional, Dict
from pydantic import BaseModel
import os
import jwt
from docx import Document
import httpx

router = APIRouter()

JWT_SECRET = os.getenv("JWT_SECRET", "supersecret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
MCP_FASTAPI_URL = os.getenv("MCP_FASTAPI_URL", "http://localhost:8000/start-analysis")
AZURE_BLOB_BASE_URL = os.getenv("AZURE_BLOB_BASE_URL", "https://<your-storage-account>.blob.core.windows.net/")

# --- Serviços utilitários ---
def validate_jwt_token(authorization: Optional[str] = Header(None)) -> Dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token JWT ausente ou inválido.")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        usuario_executor = payload.get("usuario_executor")
        email = payload.get("email")
        if not usuario_executor or not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token JWT sem campos obrigatórios.")
        return {"usuario_executor": usuario_executor, "email": email}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token JWT expirado.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token JWT inválido.")

def extract_text_from_docx(file_bytes: bytes) -> str:
    from io import BytesIO
    doc = Document(BytesIO(file_bytes))
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

class DocxUploadResponse(BaseModel):
    blob_url: str
    extracted_text: str
    job_id: str

class BlobDocxService:
    @staticmethod
    async def save_docx_to_blob(file_bytes: bytes, usuario_executor: str, projeto: str, analysis_name: str) -> str:
        # Simulação: salvaria no Azure Blob Storage real
        # Aqui, apenas monta a URL simulada
        blob_path = f"{usuario_executor}/{projeto}/arquivos_recebidos/docx/{analysis_name}.docx"
        # Aqui você usaria o SDK do Azure para salvar de fato
        # Exemplo: blob_client.upload_blob(file_bytes)
        return AZURE_BLOB_BASE_URL + blob_path

class McpClientService:
    @staticmethod
    async def start_epic_analysis(payload: dict) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(MCP_FASTAPI_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("job_id", "")

@router.post("/upload-docx", response_model=DocxUploadResponse, tags=["Upload"])
async def upload_docx(
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None),
    file: UploadFile = File(...),
    projeto: str = Form(...),
    analysis_name: str = Form(...)
):
    user_info = validate_jwt_token(authorization)
    usuario_executor = user_info["usuario_executor"]
    # 1. Ler arquivo
    file_bytes = await file.read()
    # 2. Extrair texto
    try:
        extracted_text = extract_text_from_docx(file_bytes)
    except Exception:
        raise HTTPException(status_code=400, detail="Erro ao extrair texto do arquivo docx.")
    # 3. Salvar no blob em background
    async def save_blob_task():
        await BlobDocxService.save_docx_to_blob(file_bytes, usuario_executor, projeto, analysis_name)
    background_tasks.add_task(save_blob_task)
    # 4. Construir payload para MCP
    payload = {
        "analysis_type": "criacao_epicos_azure_devops",
        "instrucoes_extras": extracted_text,
        "projeto": projeto,
        "analysis_name": analysis_name,
        "usuario_executor": usuario_executor
    }
    job_id_holder = {"job_id": ""}
    async def start_mcp_task():
        job_id = await McpClientService.start_epic_analysis(payload)
        job_id_holder["job_id"] = job_id
    background_tasks.add_task(start_mcp_task)
    # 5. Montar blob_url (simulado)
    blob_url = AZURE_BLOB_BASE_URL + f"{usuario_executor}/{projeto}/arquivos_recebidos/docx/{analysis_name}.docx"
    # 6. Retornar resposta imediata
    return DocxUploadResponse(
        blob_url=blob_url,
        extracted_text=extracted_text[:500],
        job_id=""
    )
