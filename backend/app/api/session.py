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

    # 1. Recupera informações do Job (apenas para comparar datas)
    active_job = redis_service.get_active_job_for_project(project_id)
    
    # ====================================================================
    # MUDANÇA CRÍTICA: ESTRATÉGIA DE LEITURA OTIMISTA (BLOB PRIMEIRO)
    # ====================================================================
    # Em vez de confiar no status "processing" do Redis, vamos checar 
    # se o arquivo final já existe no Blob Storage.
    
    blob_state = None
    try:
        # Carrega o estado consolidado direto da fonte de verdade (Blob)
        blob_state = await ProjectStateService.load_all_states_from_blob(usuario_executor, project_id)
    except Exception as e:
        logger.warning(f"Aviso: Não foi possível carregar blob para verificação antecipada: {e}")

    # Se conseguimos carregar o estado, vamos verificar se ele é "fresco"
    if blob_state:
        # Tenta descobrir a data deste arquivo blob
        ts_str = blob_state.get("ultima_atualizacao") or blob_state.get("last_saved_to_blob") or blob_state.get("updated_at")
        blob_timestamp = None
        
        if ts_str:
            try:
                blob_timestamp = datetime.fromisoformat(str(ts_str))
            except:
                pass
        
        # Data de inicio do job ativo (se houver)
        job_start_time = None
        if active_job and hasattr(active_job, "request_timestamp"):
            try:
                job_start_time = datetime.fromisoformat(str(active_job.request_timestamp))
            except:
                pass

        # LÓGICA DE DECISÃO:
        # Se temos um job rodando, mas o arquivo no blob é MAIS NOVO que o início do job...
        # ...então o job acabou e já salvou! Ignoramos o status 'active' do Redis.
        if job_start_time and blob_timestamp:
            if blob_timestamp >= job_start_time:
                logger.info("✅ Dados do Blob são mais recentes que o Job Ativo. Retornando 200 OK.")
                return _format_state_response(blob_state)
        
        # Se não tem job ativo, mas tem blob, retorna o blob (sucesso óbvio)
        if not active_job:
             return _format_state_response(blob_state)

    # ====================================================================
    # 2. Se chegamos aqui, o Blob é velho ou não existe.
    # Agora sim, retornamos 202 se houver job ativo.
    # ====================================================================
    if active_job:
        # Failsafe: Se o job está rodando há mais de 10 minutos, assume que travou e retorna o que tem
        if job_start_time and (datetime.utcnow() - job_start_time).total_seconds() > 600:
             logger.warning("⚠️ Job travado (>10min). Ignorando status processing.")
             if blob_state: return _format_state_response(blob_state)

        return JSONResponse(
            content={
                "status": "processing",
                "message": "O processamento está em andamento.",
                "job_id": active_job.job_id,
                "project_id": project_id
            },
            status_code=status.HTTP_202_ACCEPTED
        )

    # 3. Caso final: Sem job, sem blob -> 404
    raise HTTPException(status_code=404, detail="Projeto não encontrado ou ainda não iniciado.")

def _format_state_response(state: dict):
    """Garante que a resposta tenha os campos de lista vazios em vez de None"""
    report_fields = ["epicos", "features", "times_descricao", "alocacao_times", "premissas_riscos"]
    for field in report_fields:
        # Garante dict pai
        if state.get(field) is None:
            state[field] = {} 
        
        # Garante lista filha
        report_key = field + "_report"
        if state.get(report_key) is None: # Tenta na raiz
             if state[field].get(report_key) is None: # Tenta dentro do dict
                 state[field][report_key] = []
    return state

# ... (Mantenha os outros endpoints abaixo: get_report_state, update, save, docx) ...
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
