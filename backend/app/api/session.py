from fastapi import APIRouter, HTTPException, Body, Depends, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Dict, Optional
from backend.app.services.redis_session_service import RedisSessionService
from backend.app.services.project_state_service import ProjectStateService
from backend.app.middleware.auth_middleware import get_current_user, _extract_usuario_executor
import logging

router = APIRouter()

class UpdateReportRequest(BaseModel):
    report_data: Dict[str, Any]

@router.get("/project/{project_id}/{job_id}/reports")
async def get_project_reports(
    project_id: str,
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    usuario_executor = _extract_usuario_executor(current_user)
    logger = logging.getLogger("session_api")
    redis_service = RedisSessionService()
    redis_reports = redis_service.get_all_reports_for_project(project_id)
    if redis_reports:
        all_match = True
        for report_key, report in redis_reports.items():
            if report is not None:
                if "job_id" not in report:
                    logger.warning(f"Report '{report_key}' não possui job_id (estado legado ou erro).")
                    report["job_id"] = None
                if report["job_id"] != job_id:
                    all_match = False
                    logger.warning(f"Divergência de job_id no report '{report_key}': esperado '{job_id}', encontrado '{report['job_id']}'")
                    break
        if all_match:
            logger.info(f"✅ Relatórios encontrados no Redis com job_id correspondente ({job_id}). Retornando 200.")
            return redis_reports
    try:
        blob_state = await ProjectStateService.load_all_states_from_blob(usuario_executor, project_id)
        if blob_state:
            tem_conteudo = _check_content(blob_state)
            saved_job_id = blob_state.get("last_job_id")
            for report_key in ["epicos", "features", "times_descricao", "alocacao_times", "premissas_riscos"]:
                report = blob_state.get(report_key)
                if report is not None:
                    if "job_id" not in report:
                        logger.warning(f"Report '{report_key}' não possui job_id (estado legado ou erro).")
                        report["job_id"] = None
            if saved_job_id and saved_job_id == job_id:
                logger.info(f"✅ Blob encontrado com Job ID correspondente ({job_id}). Retornando 200.")
                return _format_state_response(blob_state)
            if saved_job_id:
                logger.warning(f"⚠️ Blob encontrado, mas Job ID diverge (Esperado: {job_id}, Encontrado: {saved_job_id}). Ignorando blob.")
    except Exception as e:
        logger.warning(f"Erro ao tentar ler blob: {e}")
    active_job = redis_service.get_active_job_for_project(project_id)
    if active_job and active_job.job_id == job_id:
        return JSONResponse(
            content={
                "status": "processing",
                "message": "O processamento deste Job ainda está em andamento.",
                "job_id": job_id,
                "project_id": project_id
            },
            status_code=status.HTTP_202_ACCEPTED
        )
    raise HTTPException(
        status_code=404, 
        detail=f"Relatório para o Job {job_id} não encontrado ou ainda não processado. Tente novamente em instantes."
    )

def _check_content(blob_state):
    chaves = ["epicos_report", "features_report", "resumo_report", "epicos", "features"]
    for chave in chaves:
        val = blob_state.get(chave)
        if val or (isinstance(val, list) and len(val) > 0):
            return True
    return False

def _format_state_response(state: dict):
    report_fields = ["epicos", "features", "times_descricao", "alocacao_times", "premissas_riscos"]
    for field in report_fields:
        if state.get(field) is None:
            state[field] = {}
        report_key = field + "_report"
        if state.get(report_key) is None:
            if state[field].get(report_key) is None:
                state[field][report_key] = []
        if "job_id" not in state[field]:
            state[field]["job_id"] = None
    return state

@router.get("/project/{project_id}/report/{report_type}")
async def get_project_report_state(project_id: str, report_type: str, current_user: dict = Depends(get_current_user)):
    logger = logging.getLogger("session_api")
    try:
        state = await ProjectStateService.get_report_state(project_id, report_type)
        if not state:
            raise HTTPException(status_code=404, detail=f"Estado do report '{report_type}' não encontrado para project_id '{project_id}'")
        if "job_id" not in state:
            logger.warning(f"Report '{report_type}' não possui job_id (estado legado ou erro).")
            state["job_id"] = None
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
