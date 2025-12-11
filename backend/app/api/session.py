from fastapi import APIRouter, HTTPException, Body, Depends, Query, status
from fastapi.responses import JSONResponse # <--- IMPORTANTE: Adicionado este import
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

    # NOVO: Busca o job ativo mais recente para o projeto
    active_job = redis_service.get_active_job_for_project(project_id)
    resumo_state = redis_service.get_session_by_project_id(project_id)
    resumo_state_dict = resumo_state.dict() if resumo_state else None
    resumo_ultima_atualizacao = None
    
    if resumo_state_dict:
        resumo_ultima_atualizacao = resumo_state_dict.get("ultima_atualizacao") or resumo_state_dict.get("last_saved_to_blob")
        if resumo_ultima_atualizacao:
            try:
                resumo_ultima_atualizacao = datetime.fromisoformat(resumo_ultima_atualizacao)
            except Exception:
                resumo_ultima_atualizacao = None
    
    # Se há job ativo (pending ou in_progress) e o estado de resumo é mais antigo que o request_timestamp do job, retorna 202
    if active_job:
        job_request_ts = active_job.request_timestamp if hasattr(active_job, "request_timestamp") else None
        
        # Lógica de verificação de timestamp
        should_return_processing = False
        if job_request_ts and resumo_ultima_atualizacao and resumo_ultima_atualizacao < job_request_ts:
            should_return_processing = True
        elif job_request_ts and not resumo_ultima_atualizacao:
            should_return_processing = True

        if should_return_processing:
            # --- CORREÇÃO AQUI: Usando JSONResponse para evitar retorno de tupla/lista ---
            return JSONResponse(
                content={
                    "status": "processing",
                    "message": "O processamento está em andamento.",
                    "job_id": active_job.job_id,
                    "project_id": project_id
                },
                status_code=status.HTTP_202_ACCEPTED
            )
            # -----------------------------------------------------------------------------

    # Se há job concluído (done) e o response_timestamp do job é mais recente que o estado de resumo, busca estado atualizado do Blob Storage
    latest_done_job = redis_service.get_latest_done_job_for_project(project_id)
    if latest_done_job:
        response_ts = latest_done_job.response_timestamp if hasattr(latest_done_job, "response_timestamp") else None
        if response_ts:
            if isinstance(response_ts, str):
                try:
                    response_ts = datetime.fromisoformat(response_ts)
                except Exception:
                    response_ts = None
            
            if resumo_ultima_atualizacao and response_ts and response_ts > resumo_ultima_atualizacao:
                try:
                    state = await ProjectStateService.load_all_states_from_blob(usuario_executor, project_id)
                    report_fields = [
                        "epicos", "features", "times_descricao", 
                        "alocacao_times", "premissas_riscos"
                    ]
                    for field in report_fields:
                        if state.get(field) is None:
                            state[field] = None
                        else:
                            report_key = field + "_report"
                            if report_key in state[field] and (state[field][report_key] is None or not isinstance(state[field][report_key], list)):
                                state[field][report_key] = []
                    return state
                except Exception as e:
                    raise HTTPException(status_code=404, detail=f"Projeto não encontrado: {e}")

    # Caso padrão: retorna o estado atual (como antes)
    try:
        state = await ProjectStateService.load_all_states_from_blob(usuario_executor, project_id)
        report_fields = [
            "epicos", "features", "times_descricao", 
            "alocacao_times", "premissas_riscos"
        ]
        for field in report_fields:
            if state.get(field) is None:
                state[field] = None
            else:
                report_key = field + "_report"
                if report_key in state[field] and (state[field][report_key] is None or not isinstance(state[field][report_key], list)):
                    state[field][report_key] = []
        return state
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Projeto não encontrado: {e}")

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
