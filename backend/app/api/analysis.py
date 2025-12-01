import logging
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel
from typing import Optional

from ..middleware.auth_middleware import get_current_user
from ..services.mcp_client_service import MCPClientService, MCPStartAnalysisPayload

router = APIRouter()
logger = logging.getLogger("analysis_api")

# Modelo de entrada para iniciar a análise (JSON Body)
class StartAnalysisRequest(BaseModel):
    projeto: str
    analysis_name: str
    analysis_type: str
    extracted_text: str  # O texto que veio do upload (ou foi editado pelo usuário)
    blob_url: Optional[str] = None # Opcional, apenas para referência se necessário

class StartAnalysisResponse(BaseModel):
    job_id: str
    message: str

@router.post("/start", response_model=StartAnalysisResponse, tags=["Analysis"])
async def start_analysis(
    payload_request: StartAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Inicia o processo de análise via MCP Server.
    Espera receber o texto já extraído (e possivelmente curado) pelo frontend.
    """
    usuario_executor = current_user.get("usuario_executor") or current_user.get("sub")

    logger.info(f"Iniciando análise '{payload_request.analysis_name}' do tipo '{payload_request.analysis_type}' para usuário {usuario_executor}")

    # 1. Montar payload para o serviço MCP
    # Mapeamos o request do front para o objeto que o MCPClientService espera
    mcp_payload = MCPStartAnalysisPayload(
        analysis_type=payload_request.analysis_type,
        instrucoes_extras=payload_request.extracted_text, # O texto do docx entra aqui como contexto/instrução
        projeto=payload_request.projeto,
        analysis_name=payload_request.analysis_name,
        usuario_executor=usuario_executor
    )

    # 2. Chamar MCP Server
    mcp_client = MCPClientService()
    try:
        mcp_response = await mcp_client.start_analysis(mcp_payload)
        job_id = mcp_response.job_id
    except Exception as e:
        logger.error(f"Erro na comunicação com MCP: {e}")
        raise HTTPException(status_code=502, detail=f"Erro ao comunicar com o servidor de Inteligência (MCP): {str(e)}")

    return StartAnalysisResponse(
        job_id=job_id,
        message="Análise solicitada com sucesso ao agente."
    )
