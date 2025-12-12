from fastapi import APIRouter, HTTPException, Body, Depends, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Dict, Optional
from backend.app.services.redis_session_service import RedisSessionService
from backend.app.services.project_state_service import ProjectStateService
from backend.app.middleware.auth_middleware import get_current_user, _extract_usuario_executor
import logging
from datetime import datetime

router = APIRouter()

class UpdateReportRequest(BaseModel):
    report_data: Dict[str, Any]

@router.get("/project/{project_id}/reports")
async def get_project_reports(
    project_id: str,
    job_id: Optional[str] = Query(None, description="ID do job para acompanhamento de status do processamento"),
    current_user: dict = Depends(get_current_user)
):
    usuario_executor = _extract_usuario_executor(current_user)
    logger = logging.getLogger("session_api")
    redis_service = RedisSessionService()

    # 1. Busca estados no Redis
    active_job = redis_service.get_active_job_for_project(project_id)
    latest_done_job = redis_service.get_latest_done_job_for_project(project_id)
    
    # ==============================================================================
    # LÓGICA ANTI-ZUMBI (CORREÇÃO CRÍTICA)
    # ==============================================================================
    if active_job:
        is_zombie = False
        
        # Regra 1: Se o ID do ativo é o mesmo do último concluído, ele já acabou.
        if latest_done_job and active_job.job_id == latest_done_job.job_id:
            is_zombie = True
            logger.info(f"👻 Job {active_job.job_id} é ZUMBI (ID igual ao último done). Ignorando status processing.")

        # Regra 2: Se o timestamp do 'done' é mais recente que o 'active', o active é velho.
        elif latest_done_job and hasattr(latest_done_job, 'request_timestamp') and hasattr(active_job, 'request_timestamp'):
            try:
                ts_done = str(latest_done_job.request_timestamp)
                ts_active = str(active_job.request_timestamp)
                if ts_done >= ts_active: # Se o done é mais novo ou igual
                    is_zombie = True
                    logger.info(f"👻 Job {active_job.job_id} é ZUMBI (Timestamp antigo). Ignorando.")
            except Exception as e:
                logger.warning(f"Erro ao comparar timestamps: {e}")

        # Se é zumbi, anulamos o active_job para forçar o código a pular para o bloco de leitura (Passo 3)
        if is_zombie:
            active_job = None
    # ==============================================================================

    resumo_state = redis_service.get_session_by_project_id(project_id)
    resumo_state_dict = resumo_state.dict() if resumo_state else None
    resumo_ultima_atualizacao = None
    
    if resumo_state_dict:
        # Tenta pegar a data de atualização mais recente possível
        candidato = resumo_state_dict.get("ultima_atualizacao") or resumo_state_dict.get("last_saved_to_blob")
        if candidato:
            try:
                resumo_ultima_atualizacao = datetime.fromisoformat(str(candidato))
            except Exception:
                resumo_ultima_atualizacao = None
    
    # 2. Bloco que retorna 202 (Processing)
    # Só entra aqui se active_job NÃO for None (ou seja, não é zumbi)
    if active_job:
        job_request_ts = None
        if hasattr(active_job, "request_timestamp") and active_job.request_timestamp:
            try:
                job_request_ts = datetime.fromisoformat(str(active_job.request_timestamp))
            except:
                pass
        
        should_return_processing = False
        
        # Se o job ativo é mais novo que a última atualização que temos salva -> Realmente está processando
        if job_request_ts and resumo_ultima_atualizacao and job_request_ts > resumo_ultima_atualizacao:
            should_return_processing = True
        
        # Se não tem dados salvos ainda -> Está processando o primeiro
        elif not resumo_ultima_atualizacao:
            should_return_processing = True

        if should_return_processing:
            return JSONResponse(
                content={
                    "status": "processing",
                    "message": "O processamento está em andamento.",
                    "job_id": active_job.job_id,
                    "project_id": project_id
                },
                status_code=status.HTTP_202_ACCEPTED
            )

    # 3. Bloco de Sucesso (200 OK)
    # Se chegou aqui, ou não tem job ativo, ou era um zumbi que ignoramos.
    try:
        # Carrega direto do Blob para garantir o dado mais fresco
        state = await ProjectStateService.load_all_states_from_blob(usuario_executor, project_id)
        
        # Inicializa campos vazios para não quebrar o frontend
        report_fields = ["epicos", "features", "times_descricao", "alocacao_times", "premissas_riscos"]
        for field in report_fields:
            if state.get(field) is None:
                state[field] = {} 
            
            report_key = field + "_report"
            if state.get(report_key) is None:
                 state[report_key] = []

        return state

    except Exception as e:
        logger.error(f"Erro ao carregar estado final: {e}")
        # Fallback: Se der erro no blob, tenta devolver o que tem no Redis
        if resumo_state_dict:
            return resumo_state_dict
        raise HTTPException(status_code=404, detail=f"Projeto não encontrado. Erro: {e}")

# ... (Mantenha os outros endpoints abaixo iguais) ...
@router.get("/project/{project_id}/report/{report_type}")
async def get_project_report_state(project_id: str, report_type: str, current_user: dict = Depends(get_current_user)):
    try:
        state = await ProjectStateService.get_report_state(project_id, report_type)
        if not state:
            raise HTTPException(status_code=404, detail=f"Estado do report '{report_type}' não encontrado para project_id '{project_id}'")
        return state
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Erro ao buscar estado do report: {e}")

@router.put("/project/{project_id}/report")
def update_project_report(project_id: str, req: UpdateReportRequest):
    redis_service = RedisSessionService()
    try:
        if not req.report_data or not isinstance(req.report_data, dict) or len(req.report_data) != 1:
            raise HTTPException(status_code=400, detail="report_data deve ser um dicionário com exatamente uma chave de relatório.")
        redis_service.update_report(project_id, req.report_data)
        session = redis_service.get_session_by_project_id(project_id)
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(ProjectStateService.save_state_to_blob(session))
        else:
            loop.run_until_complete(ProjectStateService.save_state_to_blob(session))
        return {"status": "ok", "project_id": project_id, "nome_projeto": session.nome_projeto}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao atualizar relatório: {e}")

@router.post("/project/{project_id}/save-state")
async def save_project_state(project_id: str):
    redis_service = RedisSessionService()
    try:
        session = redis_service.get_session_by_project_id(project_id)
        url = await ProjectStateService.save_state_to_blob(session)
        return {"blob_url": url, "project_id": session.project_id, "nome_projeto": session.nome_projeto}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar estado: {e}")

@router.get("/project/{project_id}/docx-files")
def get_project_docx_files(project_id: str):
    redis_service = RedisSessionService()
    try:
        session = redis_service.get_session_by_project_id(project_id)
        return {"docx_files": session.docx_files, "project_id": session.project_id, "nome_projeto": session.nome_projeto}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Projeto não encontrado: {e}")
