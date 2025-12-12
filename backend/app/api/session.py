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
    job_id: str, # Agora é obrigatório na URL
    current_user: dict = Depends(get_current_user)
):
    usuario_executor = _extract_usuario_executor(current_user)
    logger = logging.getLogger("session_api")
    redis_service = RedisSessionService()

    # 1. TENTA LER O BLOB (LEITURA FORÇADA COM VALIDAÇÃO DE JOB)
    try:
        blob_state = await ProjectStateService.load_all_states_from_blob(usuario_executor, project_id)
        
        if blob_state:
            # Verifica se o blob tem conteúdo real
            tem_conteudo = _check_content(blob_state)
            saved_job_id = blob_state.get("last_job_id")
            
            # Se o ID bater, é sucesso garantido.
            if saved_job_id and saved_job_id == job_id:
                logger.info(f"✅ Blob encontrado com Job ID correspondente ({job_id}). Retornando 200.")
                return _format_state_response(blob_state)
            
            # Se o Job ID existe mas é diferente, o blob é de outro processamento.
            if saved_job_id:
                logger.warning(f"⚠️ Blob encontrado, mas Job ID diverge (Esperado: {job_id}, Encontrado: {saved_job_id}). Ignorando blob.")

    except Exception as e:
        logger.warning(f"Erro ao tentar ler blob: {e}")

    # 2. SE O BLOB NÃO SERVIU, CHECA O REDIS PARA DAR 202
    active_job = redis_service.get_active_job_for_project(project_id)
    
    # Se o job solicitado ainda está rodando
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

    # 3. SE NÃO ESTÁ NO BLOB E NÃO ESTÁ RODANDO -> 404
    # Isso cobre o caso onde o Job ID não existe, falhou sem salvar, ou o blob ainda não sincronizou.
    raise HTTPException(
        status_code=404, 
        detail=f"Relatório para o Job {job_id} não encontrado ou ainda não processado. Tente novamente em instantes."
    )

def _check_content(blob_state):
    """Verifica se há conteúdo real no estado"""
    chaves = ["epicos_report", "features_report", "resumo_report", "epicos", "features"]
    for chave in chaves:
        val = blob_state.get(chave)
        if val or (isinstance(val, list) and len(val) > 0):
            return True
    return False

def _format_state_response(state: dict):
    """Garante que a resposta tenha os campos de lista vazios em vez de None"""
    report_fields = ["epicos", "features", "times_descricao", "alocacao_times", "premissas_riscos"]
    for field in report_fields:
        if state.get(field) is None:
            state[field] = {} 
        
        report_key = field + "_report"
        if state.get(report_key) is None:
             if state[field].get(report_key) is None:
                 state[field][report_key] = []
    return state

# ... (Outros endpoints update, save, docx permanecem iguais) ...
# Apenas a rota GET reports mudou a assinatura.
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
