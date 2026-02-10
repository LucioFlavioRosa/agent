import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.app.models.user_models import UserContext
from backend.app.services.mcp_client_service import MCPClientService

router = APIRouter()
logger = logging.getLogger("analysis_api")

class StartAnalysisRequest(BaseModel):
    email: str
    empresa: str
    nome_projeto: str
    analysis_type: str
    comentario_extra: Optional[str] = None

class StartAnalysisResponse(BaseModel):
    message: str
    project_id: Optional[str] = None
    job_id: Optional[str] = None
    nome_projeto: Optional[str] = None

@router.post("/start", response_model=StartAnalysisResponse, tags=["Analysis"])
async def start_analysis(request: StartAnalysisRequest):
    logger.info(f"Iniciando análise para projeto '{request.nome_projeto}' (analysis_type: '{request.analysis_type}') para usuário {request.email} / empresa {request.empresa}")

    # Validação mínima dos campos obrigatórios
    if not request.email or not request.empresa or not request.nome_projeto or not request.analysis_type:
        raise HTTPException(status_code=400, detail="Campos obrigatórios ausentes.")

    # Monta payload para MCP
    mcp_payload = {
        "email": request.email,
        "empresa": request.empresa,
        "nome_projeto": request.nome_projeto,
        "analysis_type": request.analysis_type,
        "comentario_extra": request.comentario_extra
    }

    mcp_client = MCPClientService()
    try:
        # Repassa o payload para MCP, sem processamento de arquivo DOCX ou enriquecimento
        mcp_response = await mcp_client.start_analysis(mcp_payload)
    except Exception as e:
        logger.error(f"Erro na comunicação com MCP: {e}")
        raise HTTPException(status_code=502, detail=f"Erro ao comunicar com o servidor de Inteligência (MCP): {str(e)}")

    return StartAnalysisResponse(
        message="Análise solicitada com sucesso ao agente.",
        project_id=getattr(mcp_response, "project_id", None),
        job_id=getattr(mcp_response, "job_id", None),
        nome_projeto=request.nome_projeto
    )
