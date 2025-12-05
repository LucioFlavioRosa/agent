import logging
from fastapi import APIRouter, HTTPException, Depends, Body, BackgroundTasks, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional

from ..middleware.auth_middleware import get_current_user, _extract_usuario_executor
from ..services.mcp_client_service import MCPClientService, MCPStartAnalysisPayload
from ..services.redis_session_service import RedisSessionService
from ..services.project_state_service import ProjectStateService
from ..services.background_state_saver import BackgroundStateSaver
from ..services.blob_storage_service import upload_and_extract_docx

import uuid

router = APIRouter()
logger = logging.getLogger("analysis_api")

class StartAnalysisResponse(BaseModel):
    message: str
    session_id: str
    project_id: Optional[str] = None

def _get_or_create_project_id(project_state: dict, provided_id: Optional[str]) -> str:
    if project_state and project_state.get("project_id"):
        return project_state.get("project_id")
    if provided_id:
        return provided_id
    return str(uuid.uuid4())

@router.post("/start", response_model=StartAnalysisResponse, tags=["Analysis"])
async def start_analysis(
    background_tasks: BackgroundTasks,
    projeto: str = Form(...),
    analysis_type: str = Form(...),
    comentario_usuario: Optional[str] = Form(None),
    project_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
    session_id: Optional[str] = Form(None)
):
    usuario_executor = _extract_usuario_executor(current_user)
    logger.info(f"Iniciando análise para projeto '{projeto}' (analysis_type: '{analysis_type}') para usuário {usuario_executor}")
    redis_service = RedisSessionService()
    project_state = await ProjectStateService.load_latest_state_from_blob(usuario_executor, projeto)
    texto_extraido = None
    blob_url = None
    project_id_final = _get_or_create_project_id(project_state, project_id)

    # Passo 5: reutilizar session_id existente se o projeto já existe
    existing_session = redis_service.get_session_by_project(usuario_executor, projeto)
    if existing_session:
        session_id_final = existing_session.session_id
        logger.info(f"Reutilizando session_id existente do Redis para projeto '{projeto}': {session_id_final}")
    else:
        session_id_from_blob = await ProjectStateService.get_session_id_from_latest_state(usuario_executor, projeto)
        if session_id_from_blob:
            session_id_final = session_id_from_blob
            logger.info(f"Reutilizando session_id do estado mais recente do Blob para projeto '{projeto}': {session_id_final}")
        else:
            session_id_final = session_id or str(uuid.uuid4())
            logger.info(f"Criando novo session_id para projeto '{projeto}': {session_id_final}")

    if not session_id_final:
        raise HTTPException(status_code=400, detail="session_id é obrigatório para iniciar análise.")

    if file is not None:
        try:
            blob_folder = f"{usuario_executor}/{projeto}/arquivos_recebidos/docx"
            blob_filename = f"{analysis_type}.docx"
            blob_url, texto_extraido = await upload_and_extract_docx(file, blob_folder, blob_filename, background_tasks)
        except ValueError as ve:
            logger.error(f"Erro de configuração do Blob Storage: {ve}")
            raise HTTPException(status_code=503, detail="Serviço de armazenamento temporariamente indisponível")
        except Exception as e:
            logger.error(f"Erro inesperado no Blob Storage ou extração: {e}")
            raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo ou extrair texto: {str(e)}")
        redis_service.create_session(
            usuario_executor,
            projeto,
            analysis_type,
            comentario_usuario=comentario_usuario,
            extracted_text=texto_extraido,
            project_id=project_id_final,
            session_id=session_id_final
        )
        try:
            redis_service.add_docx_file(session_id_final, blob_url)
        except Exception as e:
            logger.error(f"Erro ao adicionar arquivo DOCX à sessão: {e}")
        try:
            redis_service.update_session_extracted_text(session_id_final, texto_extraido)
        except Exception as e:
            logger.error(f"Erro ao salvar texto extraído na sessão: {e}")
    else:
        if project_state:
            redis_service.restore_session_from_state(
                usuario_executor,
                projeto,
                analysis_type,
                project_state,
                session_id=session_id_final
            )
            try:
                session = redis_service.get_session(session_id_final)
                texto_extraido = getattr(session, "extracted_text", None)
            except Exception as e:
                logger.error(f"Erro ao buscar texto extraído da sessão: {e}")
                texto_extraido = None
        else:
            raise HTTPException(status_code=400, detail="Para novo projeto, é obrigatório enviar um arquivo DOCX.")
    BackgroundStateSaver.schedule_periodic_save(session_id_final)
    mcp_payload = MCPStartAnalysisPayload(
        projeto=projeto,
        analysis_type=analysis_type,
        arquivo_docx=texto_extraido,
        comentario_usuario=comentario_usuario,
        usuario_executor=usuario_executor,
        session_id=session_id_final
    )
    mcp_client = MCPClientService()
    try:
        mcp_response = await mcp_client.start_analysis(mcp_payload)
    except Exception as e:
        logger.error(f"Erro na comunicação com MCP: {e}")
        raise HTTPException(status_code=502, detail=f"Erro ao comunicar com o servidor de Inteligência (MCP): {str(e)}")
    return StartAnalysisResponse(
        message="Análise solicitada com sucesso ao agente.",
        session_id=session_id_final,
        project_id=project_id_final
    )
