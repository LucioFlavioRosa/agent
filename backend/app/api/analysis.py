import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Body, BackgroundTasks, UploadFile, File, Form, Request
from pydantic import BaseModel

from ..middleware.auth_middleware import get_current_user, _extract_usuario_executor
from ..services.mcp_client_service import MCPClientService
from ..services.redis_session_service import RedisSessionService
from ..services.project_state_service import ProjectStateService
from ..services.blob_storage_service import upload_docx_to_blob
from ..services.docx_parser_service import extract_text_from_docx
from ..services.context_enrichment_service import ContextEnrichmentService

router = APIRouter()
logger = logging.getLogger("analysis_api")

class StartAnalysisResponse(BaseModel):
    message: str
    project_id: str
    job_id: str
    nome_projeto: Optional[str] = None

@router.post("/start", response_model=StartAnalysisResponse, tags=["Analysis"])
async def start_analysis(
    request: Request,
    background_tasks: BackgroundTasks,
    nome_projeto: str = Form(...),
    analysis_type: str = Form(...),
    comentario_extra: Optional[str] = Form(None),
    arquivo_docx: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    usuario_executor = _extract_usuario_executor(current_user)
    logger.info(f"Iniciando análise para projeto '{nome_projeto}' (analysis_type: '{analysis_type}') para usuário {usuario_executor}")

    if not usuario_executor or not isinstance(usuario_executor, str) or not usuario_executor.strip():
        logger.error(f"Falha ao extrair usuario_executor do token JWT: '{usuario_executor}'")
        raise HTTPException(status_code=401, detail="Campo 'usuario_executor' ausente ou inválido no token JWT.")

    if not nome_projeto or not isinstance(nome_projeto, str) or not nome_projeto.strip():
        logger.error(f"Campo 'nome_projeto' ausente ou vazio no formulário: '{nome_projeto}'")
        raise HTTPException(status_code=400, detail="Campo 'nome_projeto' ausente ou vazio no formulário.")

    redis_service = RedisSessionService()
    project_id_final = await ProjectStateService._get_project_id_by_name(usuario_executor, nome_projeto)
    project_state = None

    if project_id_final:
        project_state = await ProjectStateService.load_latest_state_from_blob(usuario_executor, project_id=project_id_final)
        try:
            redis_service.get_session_by_project_id(project_id_final)
        except Exception:
            pass
    else:
        project_id_final = str(uuid.uuid4())

    if not project_id_final or not isinstance(project_id_final, str) or not project_id_final.strip():
        logger.error(f"Falha ao gerar ou recuperar project_id_final: '{project_id_final}'")
        raise HTTPException(status_code=500, detail="Falha ao gerar ou recuperar project_id do projeto.")

    texto_extraido = None
    blob_url = None

    if arquivo_docx is not None:
        try:
            texto_extraido = await extract_text_from_docx(arquivo_docx)
        except Exception as e:
            logger.error(f"Erro ao extrair texto do docx: {e}")
            raise HTTPException(status_code=400, detail=f"Erro ao extrair texto do docx: {str(e)}")
        blob_folder = f"{usuario_executor}/{nome_projeto}/arquivos_recebidos/docx"
        blob_filename = f"{analysis_type}/{arquivo_docx.filename}"
        blob_url = await upload_docx_to_blob(
            arquivo_docx,
            blob_folder,
            blob_filename,
            background_tasks
        )

    if project_state:
        redis_service.restore_session_from_state(
            usuario_executor,
            nome_projeto,
            analysis_type,
            project_state
        )
    else:
        created_at = datetime.utcnow().isoformat()
        last_saved_to_blob = created_at
        resumo_state = {
            "nome_projeto": nome_projeto,
            "ultima_analysis_type": analysis_type,
            "created_at": created_at,
            "ultima_atualizacao": last_saved_to_blob,
            "project_id": project_id_final,
            "usuario_executor": usuario_executor
        }
        campos_obrigatorios = ["nome_projeto", "usuario_executor", "project_id"]
        campos_faltando = [
            campo for campo in campos_obrigatorios 
            if not resumo_state.get(campo) or (isinstance(resumo_state.get(campo), str) and not resumo_state.get(campo).strip())
        ]
        if campos_faltando:
            logger.critical(f"Erro crítico: Tentativa de salvar estado com campos ausentes: {campos_faltando}")
            raise HTTPException(status_code=500, detail=f"Erro interno: Estado inválido, campos faltando: {campos_faltando}")
        redis_service.create_session(
            usuario_executor,
            nome_projeto,
            analysis_type,
            project_id=project_id_final,
            extracted_text=texto_extraido,
            initial_state=resumo_state
        )
        logger.info(f"Salvando novo estado no Blob Storage para {usuario_executor}, Projeto: {nome_projeto}, ID: {project_id_final}")
        await ProjectStateService.save_state_to_blob(resumo_state)

    if blob_url:
        redis_service.add_docx_file(project_id_final, blob_url)

    instrucoes_extras = comentario_extra
    try:
        instrucoes_extras_enriquecidas = await ContextEnrichmentService.enrich_instructions(
            usuario_executor=usuario_executor,
            nome_projeto=nome_projeto,
            project_id=project_id_final,
            analysis_type=analysis_type,
            instrucoes_extras=instrucoes_extras
        )
        logger.debug(f"[ANALYSIS] instrucoes_extras_enriquecidas para MCP: '{instrucoes_extras_enriquecidas}'")
        logger.debug(f"[ANALYSIS] Tamanho instrucoes_extras_enriquecidas: {len(instrucoes_extras_enriquecidas) if instrucoes_extras_enriquecidas else 0}")
        logger.debug(f"[ANALYSIS] Preview instrucoes_extras_enriquecidas: '{instrucoes_extras_enriquecidas[:500] if instrucoes_extras_enriquecidas else ''}'")
        logger.debug(f"[ANALYSIS] Preview comentario_extra original: '{comentario_extra[:500] if comentario_extra else ''}'")
    except Exception as e:
        logger.error(f"Erro ao enriquecer instrucoes_extras: {e}")
        if analysis_type.startswith("refinamento_"):
            raise HTTPException(status_code=500, detail=f"Erro ao enriquecer contexto/refinamento: {str(e)}")
        instrucoes_extras_enriquecidas = instrucoes_extras

    logger.debug(f"[ANALYSIS] MCP PAYLOAD instrucoes_extras_enriquecidas: '{instrucoes_extras_enriquecidas}'")

    # Gera job_id e salva job no Redis antes de enviar ao MCP
    job_id = redis_service.create_job(project_id_final, analysis_type)

    mcp_payload = {
        "project_id": project_id_final,
        "texto_extraido_do_docx": texto_extraido,
        "comentario_extra": instrucoes_extras_enriquecidas,
        "analysis_type": analysis_type,
        "job_id": job_id
    }
    logger.debug(f"[ANALYSIS] Payload enviado ao MCP: {mcp_payload}")

    mcp_client = MCPClientService()
    try:
        await mcp_client.start_analysis(mcp_payload)
    except Exception as e:
        logger.error(f"Erro na comunicação com MCP: {e}")
        raise HTTPException(status_code=502, detail=f"Erro ao comunicar com o servidor de Inteligência (MCP): {str(e)}")

    return StartAnalysisResponse(
        message="Análise solicitada com sucesso ao agente.",
        project_id=project_id_final,
        job_id=job_id,
        nome_projeto=nome_projeto
    )
