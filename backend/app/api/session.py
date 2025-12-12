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

    # 1. Recupera o Job Ativo do Redis (Apenas para referência de data)
    active_job = redis_service.get_active_job_for_project(project_id)
    
    # 2. ESTRATÉGIA OTIMISTA: Tenta carregar o Estado Final do Blob PRIMEIRO
    # Em vez de confiar cegamente no status "processing" do Redis, vamos ver se o dado já existe.
    blob_state = None
    blob_timestamp = None
    
    try:
        # Carrega o estado consolidado direto da fonte de verdade (Blob Storage)
        blob_state = await ProjectStateService.load_all_states_from_blob(usuario_executor, project_id)
        
        # Tenta descobrir a data deste arquivo blob para comparação
        if blob_state:
            # Procura por campos de data comuns que o seu sistema usa
            ts_str = blob_state.get("ultima_atualizacao") or blob_state.get("last_saved_to_blob") or blob_state.get("updated_at")
            if ts_str:
                try:
                    blob_timestamp = datetime.fromisoformat(str(ts_str))
                except:
                    pass
    except Exception as e:
        logger.warning(f"Não foi possível carregar estado do blob para verificação antecipada: {e}")

    # 3. Lógica de Decisão: 200 (Pronto) vs 202 (Processando)
    should_return_processing = False
    
    if active_job:
        job_request_ts = None
        if hasattr(active_job, "request_timestamp") and active_job.request_timestamp:
            try:
                job_request_ts = datetime.fromisoformat(str(active_job.request_timestamp))
            except:
                pass
        
        # Se temos data do job e data do blob
        if job_request_ts:
            if blob_timestamp:
                # O X DA QUESTÃO (Solução do Erro):
                # Se o Blob é MAIS NOVO ou IGUAL ao Job -> O Job terminou e salvou!
                # Entregamos o resultado (200 OK) e ignoramos o status processing.
                if blob_timestamp >= job_request_ts:
                    should_return_processing = False 
                    logger.info(f"✅ Blob (ts={blob_timestamp}) é mais novo que Active Job (ts={job_request_ts}). Retornando sucesso imediato.")
                else:
                    should_return_processing = True # Blob é velho, realmente está processando.
            else:
                # Temos job mas não temos data no blob -> Provavelmente processando
                should_return_processing = True
                
                # Anti-Travamento (Failsafe): 
                # Se o job já tem mais de 5 minutos, assume que o Redis travou e entrega o que tem.
                if (datetime.utcnow() - job_request_ts).total_seconds() > 300:
                     logger.warning("⚠️ Job ativo há muito tempo (>5min). Ignorando status processing e retornando estado atual.")
                     should_return_processing = False

    # Retorno 202 (Apenas se confirmamos que está processando E os dados no blob são velhos)
    if should_return_processing and active_job:
        return JSONResponse(
            content={
                "status": "processing",
                "message": "O processamento está em andamento.",
                "job_id": active_job.job_id,
                "project_id": project_id
            },
            status_code=status.HTTP_202_ACCEPTED
        )

    # 4. Retorno 200 (Estado Final)
    if blob_state:
        # Garante estrutura mínima para o frontend não quebrar
        report_fields = ["epicos", "features", "times_descricao", "alocacao_times", "premissas_riscos"]
        for field in report_fields:
            if blob_state.get(field) is None:
                blob_state[field] = {} 
            
            report_key = field + "_report"
            if blob_state.get(report_key) is None:
                 blob_state[report_key] = [] # Garante lista vazia em vez de None

        return blob_state

    # Se chegou aqui, não tem job ativo e não tem estado no blob
    raise HTTPException(status_code=404, detail="Projeto não encontrado ou ainda não iniciado.")

# ... (Mantenha os outros endpoints inalterados abaixo: get_report_state, update, save, etc.) ...
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
