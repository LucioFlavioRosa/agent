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
        
        # 1. Atualização de Status Intermediário
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

            # B. Atualiza Redis (Dados de Negócio)
            redis_service.update_report(payload.project_id, report_data)
            
            # C. Prepara Dados Comuns
            agora_dt = datetime.utcnow()
            agora_iso = agora_dt.isoformat()
            
            # D. Recupera Sessão Completa para Salvar o Relatório (Epicos/Features/etc)
            session = redis_service.get_session_by_project_id(payload.project_id)
            
            if session:
                # Atualiza Timestamps e Job ID no objeto principal
                if hasattr(session, "ultima_atualizacao"): session.ultima_atualizacao = agora_dt
                if hasattr(session, "last_saved_to_blob"): session.last_saved_to_blob = agora_dt
                if hasattr(session, "last_job_id"): session.last_job_id = payload.job_id
                
                # Fallback Dict
                if isinstance(session, dict):
                    session["ultima_atualizacao"] = agora_iso
                    session["last_saved_to_blob"] = agora_iso
                    session["last_job_id"] = payload.job_id

                if hasattr(session, "project_id") and not session.project_id:
                    session.project_id = payload.project_id
                
                # 1º SAVE: Salva o Relatório Específico (ex: Epicos)
                # O ProjectStateService detecta que tem 'epicos_report' e salva na pasta /epicos/
                await ProjectStateService.save_state_to_blob(session)
                logger.info("Relatório específico salvo no Blob Storage.")

                # ==============================================================================
                # E. NOVO PASSO: FORÇAR ATUALIZAÇÃO DO ARQUIVO DE RESUMO
                # ==============================================================================
                # Criamos um objeto enxuto SÓ com metadados. 
                # Como não tem chaves de relatório (ex: epicos_report), 
                # o ProjectStateService vai salvar automaticamente na pasta /resumo/
                
                resumo_update = {
                    "usuario_executor": getattr(session, "usuario_executor", "") or session.get("usuario_executor"),
                    "nome_projeto": getattr(session, "nome_projeto", "") or session.get("nome_projeto"),
                    "project_id": payload.project_id,
                    "last_job_id": payload.job_id,  # <--- O REI DA FESTA ESTÁ AQUI
                    "ultima_analysis_type": payload.analysis_type,
                    "ultima_atualizacao": agora_iso,
                    "last_saved_to_blob": agora_iso,
                    "created_at": getattr(session, "created_at", agora_iso) if hasattr(session, "created_at") else session.get("created_at", agora_iso)
                }
                
                # Conversão de datetime para string se necessário para o dict
                if isinstance(resumo_update["created_at"], datetime):
                    resumo_update["created_at"] = resumo_update["created_at"].isoformat()

                # 2º SAVE: Salva o Resumo Atualizado
                await ProjectStateService.save_state_to_blob(resumo_update)
                logger.info(f"Arquivo de Resumo atualizado com last_job_id: {payload.job_id}")
                # ==============================================================================

            # F. FINALMENTE: Marca o Job como DONE
            redis_service.update_job_status(payload.job_id, "done")
            logger.info(f"Job {payload.job_id} finalizado e marcado como DONE no Redis.")

            return {"status": "ok", "project_id": payload.project_id}

    except Exception as e:
        logger.error(f"Erro crítico no webhook: {e}")
        try:
            redis_service.update_job_status(payload.job_id, "error")
        except:
            pass
        raise HTTPException(status_code=500, detail=str(e))
