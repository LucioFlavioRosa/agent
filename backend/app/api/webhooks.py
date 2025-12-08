import logging
from fastapi import APIRouter, HTTPException, status, Request
from backend.app.models.mcp_webhook_models import MCPWebhookPayload
from backend.app.services.redis_session_service import RedisSessionService
from backend.app.services.project_state_service import ProjectStateService

router = APIRouter()
logger = logging.getLogger("webhooks_api")

@router.post("/mcp", status_code=200, tags=["Webhooks"])
async def mcp_webhook(payload: MCPWebhookPayload, request: Request):
    redis_service = RedisSessionService()
    logger.info(f"Recebido webhook MCP para job_id: {payload.job_id}, status: {payload.status}, project_id: {getattr(payload, 'project_id', None)}")
    try:
        if not getattr(payload, 'project_id', None):
            logger.error(f"Webhook recebido sem project_id. Payload inválido.")
            raise HTTPException(status_code=400, detail="project_id é obrigatório no webhook MCP.")
        session = redis_service.get_session_by_project_id(payload.project_id)
        if not session:
            logger.error(f"Webhook recebido para project_id não encontrado: {payload.project_id}. Estado do Redis pode estar inconsistente.")
            raise HTTPException(status_code=404, detail=f"Sessão não encontrada para project_id: {payload.project_id}")
        if payload.status == "in_progress":
            logger.info(f"Webhook MCP status 'in_progress' recebido para project_id {payload.project_id}. Nenhuma atualização de estado será feita.")
            return {"status": "ok", "project_id": payload.project_id, "nome_projeto": session.nome_projeto}
        elif payload.status == "done":
            report_data = payload.report_data
            if not report_data or not isinstance(report_data, dict) or len(report_data) != 1:
                logger.error(f"Estrutura de report_data inválida para project_id '{payload.project_id}'")
                raise HTTPException(status_code=400, detail=f"Estrutura de report_data inválida")
            report_field = list(report_data.keys())[0]
            logger.debug(f"[WEBHOOK] Antes da atualização: {[getattr(session, rf, None) for rf in ['epicos_report','features_report','times_descricao_report','alocacao_times_report','premissas_riscos_report']]}")
            redis_service.update_report(payload.project_id, report_data)
            session = redis_service.get_session_by_project_id(payload.project_id)
            logger.debug(f"[WEBHOOK] Depois da atualização: {[getattr(session, rf, None) for rf in ['epicos_report','features_report','times_descricao_report','alocacao_times_report','premissas_riscos_report']]}")
            await ProjectStateService.save_state_to_blob(session)
            state = session.to_project_state()
            return {"status": "ok", "project_id": payload.project_id, "nome_projeto": session.nome_projeto, "state": state}
        elif payload.status == "error":
            logger.error(f"Webhook de erro recebido: job_id={payload.job_id}, error_type={payload.error_type}, error_message={payload.error_message}")
            return {"status": "ok", "project_id": payload.project_id, "nome_projeto": session.nome_projeto}
        return {"status": "ok", "project_id": payload.project_id, "nome_projeto": session.nome_projeto}
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        logger.error(f"Erro ao processar webhook MCP: {exc}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar webhook MCP.")
