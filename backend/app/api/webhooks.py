import os
import json
import logging
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Request, status, Depends

from backend.app.services.redis_session_service import RedisSessionService
from backend.app.services.mongodb_service import MongoDBService
from backend.config.agent_mapping import AGENT_TO_CATEGORY

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
    category: str # ex: 'epics', 'features', etc. (Enviado pelo MCP como fallback)
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
            # --- Busca metadados do job no Redis ---
            job_meta = await redis_service.get_job(job_id)
            
            # (Se o job_meta for um Pydantic Model, converta para dict ou use getattr)
            # Como a implementação exata de get_job() está no redis_session_service.py, 
            # vou tratar como um dicionário ou objeto que tenha os atributos abaixo.
            analysis_type = job_meta.get("analysis_type", "unknown") if isinstance(job_meta, dict) else getattr(job_meta, "analysis_type", "unknown")
            created_by_email = job_meta.get("email", "unknown") if isinstance(job_meta, dict) else getattr(job_meta, "email", "unknown")
            
            # 🚀 NOVO: Resgata o contexto congelado do Redis
            context_used = job_meta.get("context_used", {}) if isinstance(job_meta, dict) else getattr(job_meta, "context_used", {})

            # ---------------------------------------------------------
            # 2. A MÁGICA DO MAPEAMENTO ACONTECE AQUI
            # ---------------------------------------------------------
            report_category = AGENT_TO_CATEGORY.get(analysis_type, payload.category)

            # --- Lógica para calcular a NOVA VERSÃO dinamicamente ---
            history_count = await mongo_service.db.project_reports_history.count_documents({
                "project_id": payload.project_id,
                "report_category": report_category 
            })
            nova_versao = history_count + 1

            # 3. MongoDB (Ledger): Insere histórico detalhado
            report_history_record = {
                "job_id": job_id,
                "project_id": payload.project_id,
                "company_id": payload.company_id,
                "report_category": report_category,      
                "analysis_type": analysis_type,          
                "version": nova_versao,                  
                "status": "done",
                "blob_path": payload.blob_path,
                "created_by_email": created_by_email,
                "created_at": datetime.utcnow(),
                
                # 🚀 NOVO: Salva a linhagem congelada neste registro histórico!
                "context_used": context_used
            }
            await mongo_service.db.project_reports_history.insert_one(report_history_record)
            msg += f" | Ledger salvo (Versão {nova_versao})."

            # 4. MongoDB (Ponteiro): Atualiza latest_reports no projeto
            # 🚀 NOVO: Se este relatório foi gerado usando contexto do passado, 
            # o projeto inteiro deve retroceder para esses ponteiros antigos também.
            
            # Prepara o objeto de atualização com a VERSÃO NOVA gerada agora
            update_data = {
                f"latest_reports.{report_category}": job_id,
                "updated_at": datetime.utcnow()
            }
            
            # Se existia contexto, nós empurramos ele para o latest_reports também.
            for key, past_job_id in context_used.items():
                if key.endswith("_job_id"):
                    # Extrai a categoria da chave (ex: de "features_job_id" tira "features")
                    dep_category = key.replace("_job_id", "")
                    
                    # 🚀 A CORREÇÃO: Nunca sobrescrever a categoria atual com a versão do passado!
                    if dep_category != report_category:
                        update_data[f"latest_reports.{dep_category}"] = past_job_id

            # Conversão segura para ObjectId caso o banco o exija
            try:
                from bson import ObjectId
                obj_project_id = ObjectId(payload.project_id)
            except Exception:
                obj_project_id = payload.project_id

            # Executa o update no projeto com todos os campos de uma vez
            await mongo_service.db.projects.update_one(
                {"_id": obj_project_id}, 
                {"$set": update_data}
            )
            msg += " | Ponteiro do projeto (e seu contexto) atualizados."

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
