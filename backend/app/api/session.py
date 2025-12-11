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

    # 1. Busca os estados no Redis
    active_job = redis_service.get_active_job_for_project(project_id)
    latest_done_job = redis_service.get_latest_done_job_for_project(project_id)
    
    # --- CORREÇÃO DO "ZUMBI 202" ---
    # Verifica se o job que consta como ativo na verdade já terminou (está no latest_done_job)
    is_active_actually_done = False
    if active_job and latest_done_job:
        if active_job.job_id == latest_done_job.job_id:
            is_active_actually_done = True
            logger.info(f"Job {active_job.job_id} consta como ativo mas já foi finalizado. Ignorando status processing.")

    # Se descobrimos que ele já acabou, anulamos a variável active_job para pular o bloco do 202
    if is_active_actually_done:
        active_job = None
    # -------------------------------

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
    
    # 2. Bloco que retorna 202 (Processing)
    if active_job:
        job_request_ts = active_job.request_timestamp if hasattr(active_job, "request_timestamp") else None
        
        should_return_processing = False
        
        # Cenário A: Temos um resumo, mas o job é mais novo que o resumo (dados desatualizados)
        if job_request_ts and resumo_ultima_atualizacao and resumo_ultima_atualizacao < job_request_ts:
            should_return_processing = True
        
        # Cenário B: Não temos resumo nenhum ainda
        elif job_request_ts and not resumo_ultima_atualizacao:
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

    # 3. Bloco que retorna 200 (Done) - Recuperação Inteligente
    # Se chegamos aqui, ou não tem job ativo, ou o job ativo já terminou.
    
    # Vamos verificar se precisamos forçar uma leitura do Blob (caso o cache local esteja velho)
    if latest_done_job:
        response_ts = latest_done_job.response_timestamp if hasattr(latest_done_job, "response_timestamp") else None
        if response_ts:
            if isinstance(response_ts, str):
                try:
                    response_ts = datetime.fromisoformat(response_ts)
                except Exception:
                    response_ts = None
            
            # Se a resposta do job é mais nova que o que temos salvo no estado do projeto -> Reload do Blob
            if resumo_ultima_atualizacao and response_ts and response_ts > resumo_ultima_atualizacao:
                try:
                    state = await ProjectStateService.load_all_states_from_blob(usuario_executor, project_id)
                    # Garante estrutura mínima
                    report_fields = ["epicos", "features", "times_descricao", "alocacao_times", "premissas_riscos"]
                    for field in report_fields:
                        if state.get(field) is None:
                            state[field] = None
                        else:
                            report_key = field + "_report"
                            if report_key in state[field] and (state[field][report_key] is None or not isinstance(state[field][report_key], list)):
                                state[field][report_key] = []
                    return state
                except Exception as e:
                    # Se falhar no blob, cai para o retorno padrão abaixo
                    logger.error(f"Erro ao recarregar do blob: {e}")
                    pass 

    # 4. Caso padrão: Retorna o que tem no estado atual
    try:
        state = await ProjectStateService.load_all_states_from_blob(usuario_executor, project_id)
        report_fields = ["epicos", "features", "times_descricao", "alocacao_times", "premissas_riscos"]
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

# ... (Resto dos endpoints mantidos iguais) ...
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
