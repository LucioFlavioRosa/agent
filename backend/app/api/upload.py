from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends, Request, status
from fastapi.responses import JSONResponse
from typing import Optional
from pydantic import BaseModel
import os
from ..middleware.auth_middleware import get_current_user
from ..services.blob_storage_service import upload_docx_to_blob
from ..services.docx_parser_service import extract_text_from_docx
from ..services.mcp_client_service import MCPClientService

router = APIRouter()

class UploadDocxResponse(BaseModel):
    job_id: str
    blob_url: str
    message: str

@router.post("/upload/docx", response_model=UploadDocxResponse, tags=["Upload"])
async def upload_docx(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    projeto: str = Form(...),
    analysis_name: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    # 1. Extrair usuario_executor do JWT
    usuario_executor = current_user.get("usuario_executor") or current_user.get("sub")
    if not usuario_executor:
        raise HTTPException(status_code=401, detail="Usuário não autenticado no token.")
    # 2. Validar extensão
    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Apenas arquivos .docx são permitidos.")
    # 3. Extrair texto do docx
    try:
        texto_extraido = await extract_text_from_docx(file)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao extrair texto do docx: {str(e)}")
    # 4. Salvar arquivo no Blob Storage (em background)
    blob_folder = f"{usuario_executor}/{projeto}/arquivos_recebidos/docx"
    blob_filename = f"{analysis_name}.docx"
    blob_url = await upload_docx_to_blob(file, blob_folder, blob_filename, background_tasks)
    # 5. Montar payload para MCP
    payload = {
        "analysis_type": "criacao_epicos_azure_devops",
        "instrucoes_extras": texto_extraido,
        "projeto": projeto,
        "analysis_name": analysis_name,
        "usuario_executor": usuario_executor
    }
    # 6. Chamar MCP Server
    mcp_client = MCPClientService()
    try:
        job_id = await mcp_client.start_analysis(payload)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao comunicar com MCP Server: {str(e)}")
    return UploadDocxResponse(job_id=job_id, blob_url=blob_url, message="Arquivo recebido, salvo e análise iniciada com sucesso.")
