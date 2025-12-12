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
    active_job = redis_service.get_active_job_for_project(project_id)
    latest_done_job = redis_service.get_latest_done_job_for_project(project_id)
    redis_state = redis_service.get_resumo_state(project_id)
    blob_state = None
    try:
        blob_state = await ProjectStateService.load_all_states_from_blob(usuario_executor, project_id)
    except Exception as e:
        logger.warning(f"Aviso: Não foi possível carregar blob para verificação antecipada: {e}")
    blob_timestamp = None
    if blob_state:
        ts_str = blob_state.get("ultima_atualizacao") or blob_state.get("last_saved_to_blob") or blob_state.get("updated_at")
        if ts_str:
            try:
                blob_timestamp = datetime.fromisoformat(str(ts_str))
            except:
                pass
    job_start_time = None
    if active_job and hasattr(active_job, "request_timestamp"):
        try:
            job_start_time = datetime.fromisoformat(str(active_job.request_timestamp))
        except:
            pass
    done_job_response_ts = None
    if latest_done_job and hasattr(latest_done_job, "response_timestamp") and latest_done_job.response_timestamp:
        try:
            done_job_response_ts = datetime.fromisoformat(str(latest_done_job.response_timestamp))
        except:
            pass
    # NOVA LÓGICA: Se houver job 'done' e response_timestamp, comparar com blob/redis
    if done_job_response_ts:
        # Se blob é mais recente que response_timestamp, retorna blob
        if blob_timestamp and blob_timestamp >= done_job_response_ts:
            logger.info("✅ Dados do Blob são mais recentes que o último job DONE. Retornando 200 OK.")
            return _format_state_response(blob_state)
        # Se redis é mais recente que response_timestamp, retorna redis
        redis_timestamp = None
        if redis_state:
            redis_ts_str = redis_state.get("ultima_atualizacao") or redis_state.get("last_saved_to_blob") or redis_state.get("updated_at")
            if redis_ts_str:
                try:
                    redis_timestamp = datetime.fromisoformat(str(redis_ts_str))
                except:
                    pass
        if redis_timestamp and redis_timestamp >= done_job_response_ts:
            logger.info("✅ Dados do Redis são mais recentes que o último job DONE. Retornando 200 OK.")
            return _format_state_response(redis_state)
        # Se response_timestamp é mais recente, força leitura do blob
        if blob_state:
            logger.info("✅ Retornando blob pois job está DONE e blob disponível.")
            return _format_state_response(blob_state)
        if redis_state:
            logger.info("✅ Retornando redis pois job está DONE e blob não disponível.")
            return _format_state_response(redis_state)
        raise HTTPException(status_code=404, detail="Projeto não encontrado ou ainda não iniciado.")
    # Se job ativo (pending/in_progress)
    if active_job:
        if job_start_time and (datetime.utcnow() - job_start_time).total_seconds() > 600:
            logger.warning("⚠️ Job travado (>10min). Ignorando status processing.")
            if blob_state:
                return _format_state_response(blob_state)
            if redis_state:
                return _format_state_response(redis_state)
        return JSONResponse(
            content={
                "status": "processing",
                "message": "O processamento está em andamento.",
                "job_id": active_job.job_id,
                "project_id": project_id
            },
            status_code=status.HTTP_202_ACCEPTED
        )
    # Se não há job ativo, retorna blob ou redis
    if blob_state:
        return _format_state_response(blob_state)
    if redis_state:
        return _format_state_response(redis_state)
    raise HTTPException(status_code=404, detail="Projeto não encontrado ou ainda não iniciado.")

def _format_state_response(state: dict):
    report_fields = ["epicos", "features", "times_descricao", "alocacao_times", "premissas_riscos"]
    for field in report_fields:
        if state.get(field) is None:
            state[field] = {}
        report_key = field + "_report"
        if state.get(report_key) is None:
            if state[field].get(report_key) is None:
                state[field][report_key] = []
    return state

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
