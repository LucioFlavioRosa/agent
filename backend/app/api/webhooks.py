import logging
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Request, status, Depends

from backend.app.services.redis_session_service import RedisSessionService
from backend.app.services.mongodb_service import MongoDBService

router = APIRouter()
logger = logging.getLogger("webhooks_api")

def get_redis_service() -> RedisSessionService:
    return RedisSessionService()

async def get_mongo_service(request: Request) -> MongoDBService:
    return request.app.state.mongo_service

# Contrato esperado do Callback do MCP
class JobCompletePayload(BaseModel):
    project_id: str
    company_id: str
    status: str
    category: str # ex: 'epics', 'features', etc.
    blob_path: Optional[str] = None
    error_message: Optional[str] = None

@router.post("/internal/jobs/{job_id}/complete", status_code=status.HTTP_200_OK, tags=["Webhooks"])
async def mcp_job_complete_webhook(
    job_id: str,
    payload: JobCompletePayload,
    request: Request,
    redis_service: RedisSessionService = Depends(get_redis_service),
    mongo_service: MongoDBService = Depends(get_mongo_service)
):
    logger.info(f"[Webhook] Callback recebido: job_id={job_id}, status={payload.status}, company={payload.company_id}")

    try:
        # 1. Redis: Atualiza de pending para done (ou error)
        await redis_service.update_job_status(job_id, payload.status)
        msg = f"Job {job_id} atualizado para {payload.status}."

        if payload.status == "done":
            # --- NOVO: Busca metadados do job no Redis ---
            job_meta = await redis_service.get_job(job_id)
            analysis_type = getattr(job_meta, "analysis_type", "unknown") if job_meta else "unknown"
            created_by_email = getattr(job_meta, "email", "unknown") if job_meta else "unknown"

            # --- NOVO: Lógica para calcular a NOVA VERSÃO dinamicamente ---
            history_count = await mongo_service.db.project_reports_history.count_documents({
                "project_id": payload.project_id,
                "report_category": payload.category
            })
            nova_versao = history_count + 1

            # 2. MongoDB (Ledger): Insere histórico detalhado
            report_history_record = {
                "job_id": job_id,
                "project_id": payload.project_id,
                "company_id": payload.company_id,
                "report_category": payload.category,     # ex: 'epics'
                "analysis_type": analysis_type,          # ex: 'agent_epics_generator_digital'
                "version": nova_versao,                  # 1, 2, 3...
                "status": "done",
                "blob_path": payload.blob_path,
                "created_by_email": created_by_email,
                "created_at": datetime.utcnow()
            }
            await mongo_service.db.project_reports_history.insert_one(report_history_record)
            msg += f" | Ledger salvo (Versão {nova_versao})."

            # 3. MongoDB (Ponteiro): Atualiza latest_reports no projeto
            update_field = f"latest_reports.{payload.category}"
            await mongo_service.db.projects.update_one(
                {"_id": payload.project_id}, # Ajuste para ObjectId(payload.project_id) se você não armazena como string
                {"$set": {update_field: job_id, "updated_at": datetime.utcnow()}}
            )
            msg += " | Ponteiro do projeto atualizado."

        elif payload.status == "error":
            err_msg = payload.error_message or "Erro desconhecido processado pelo MCP."
            await redis_service.store_error_message_for_job(job_id, err_msg)
            msg += " | Erro registrado."

        logger.info(f"[Webhook] Finalizado com sucesso: {msg}")
        return {"status": "ok", "job_id": job_id, "msg": msg}

    except Exception as e:
        logger.error(f"[Webhook] Erro na orquestração de dados para job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Erro interno ao persistir dados do webhook."
        )
