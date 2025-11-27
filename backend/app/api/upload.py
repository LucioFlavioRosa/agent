from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends, Request, status
from fastapi.responses import JSONResponse
from typing import Optional
from pydantic import BaseModel
import os
from ..middleware.auth_middleware import get_current_user
from ..services.blob_storage_service import upload_docx_to_blob
from ..services.docx_parser_service import extract_text_from_docx
from ..services.mcp_client_service import MCPClientService, MCPStartAnalysisPayload

router = APIRouter()

class UploadDocxResponse(BaseModel):
    job_id: str
    blob_url: str
    message: str

@router.post("/docx", response_model=UploadDocxResponse, tags=["Upload"])
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
    # A dependência já garante que o usuário está autenticado e lança erro específico se não estiver
    # 2. Validar extensão
    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Apenas arquivos .docx são permitidos.")
    # 3. Extrair texto do docx usando serviço
    try:
        texto_extraido = await extract_text_from_docx(file)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao extrair texto do docx: {str(e)}")
    # 4. Salvar arquivo no Blob Storage (em background) usando serviço
    blob_folder = f"{usuario_executor}/{projeto}/arquivos_recebidos/docx"
    blob_filename = f"{analysis_name}.docx"
    blob_url = await upload_docx_to_blob(file, blob_folder, blob_filename, background_tasks)
    # 5. Montar payload para MCP: analysis_type, projeto, analysis_name do frontend; instrucoes_extras e usuario_executor do backend
    payload = MCPStartAnalysisPayload(
        analysis_type=analysis_type,
        instrucoes_extras=texto_extraido,
        projeto=projeto,
        analysis_name=analysis_name,
        usuario_executor=usuario_executor
    )
    # 6. Chamar MCP Server
    mcp_client = MCPClientService()
    try:
        mcp_response = await mcp_client.start_analysis(payload)
        job_id = mcp_response.job_id
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao comunicar com MCP Server: {str(e)}")
    return UploadDocxResponse(job_id=job_id, blob_url=blob_url, message="Arquivo recebido, salvo e análise iniciada com sucesso.")
