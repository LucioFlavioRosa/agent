import logging
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Request
from backend.app.models.mcp_webhook_models import MCPWebhookPayload
from backend.app.services.redis_session_service import RedisSessionService
from backend.app.services.project_state_service import ProjectStateService

router = APIRouter()
logger = logging.getLogger("webhooks_api")

@router.post("/mcp", status_code=200, tags=["Webhooks"])
async def mcp_webhook(payload: MCPWebhookPayload, request: Request):
    redis_service = RedisSessionService()
    logger.info(f"webhook_start: job_id={payload.job_id}, status={payload.status}")

    try:
        # Validações Básicas
        if not getattr(payload, 'project_id', None):
            raise HTTPException(status_code=400, detail="project_id é obrigatório.")
        
        # 1. Atualização de Status Intermediário (Se for o caso)
        if payload.status == "in_progress":
            redis_service.update_job_status(payload.job_id, "in_progress")
            return {"status": "ok", "msg": "Job marcado como in_progress"}

        # 2. Tratamento de Erro
        if payload.status == "error":
            redis_service.update_job_status(payload.job_id, "error")
            logger.error(f"Job falhou: {payload.error_message}")
            return {"status": "ok", "msg": "Job marcado como error"}

        # 3. Tratamento de Sucesso (DONE)
        if payload.status == "done":
            # A. Valida Payload
            report_data = payload.report_data
            if not report_data or not isinstance(report_data, dict):
                raise HTTPException(status_code=400, detail="report_data inválido")

            # B. Atualiza Sessão/Relatório no Redis (Dados de Negócio)
            redis_service.update_report(payload.project_id, report_data)
            
            # C. Atualiza Blob Storage (Persistência)
            # C. Atualiza Blob Storage (Persistência)
            session = redis_service.get_session_by_project_id(payload.project_id)
            if session:
                # --- MUDANÇA AQUI: Use o objeto datetime, não a string ---
                agora_dt = datetime.utcnow() 
                # ---------------------------------------------------------
                
                # Verifica e atribui
                if hasattr(session, "last_saved_to_blob"):
                    session.last_saved_to_blob = agora_dt # Atribui objeto datetime
                
                if hasattr(session, "ultima_atualizacao"):
                    session.ultima_atualizacao = agora_dt # Atribui objeto datetime
                
                # Fallback para dict
                if isinstance(session, dict):
                    session["last_saved_to_blob"] = agora_dt.isoformat()
                    session["ultima_atualizacao"] = agora_dt.isoformat()

                if hasattr(session, "project_id") and not session.project_id:
                    session.project_id = payload.project_id
                
                # Salva no Blob
                await ProjectStateService.save_state_to_blob(session)

            # D. FINALMENTE: Marca o Job como DONE no Redis (Controle de Fluxo)
            # Isso é a última coisa a fazer para evitar condição de corrida
            redis_service.update_job_status(payload.job_id, "done")
            logger.info(f"Job {payload.job_id} finalizado e marcado como DONE no Redis.")

            return {"status": "ok", "project_id": payload.project_id}

    except Exception as e:
        logger.error(f"Erro crítico no webhook: {e}")
        # Mesmo no erro, tentamos marcar o job como erro para não travar o front
        try:
            redis_service.update_job_status(payload.job_id, "error")
        except:
            pass
        raise HTTPException(status_code=500, detail=str(e))
