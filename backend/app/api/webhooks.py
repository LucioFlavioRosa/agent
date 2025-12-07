import logging
from fastapi import APIRouter, HTTPException, status, Request
from backend.app.models.mcp_webhook_models import MCPWebhookPayload
from backend.app.services.redis_session_service import RedisSessionService
from backend.app.utils.webhook_validator import validate_report_data_structure
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
        logger.info(f"Buscando sessão associada ao project_id: {payload.project_id}")
        session = redis_service.get_session_by_project_id(payload.project_id)
        if not session:
            logger.error(f"Webhook recebido para project_id não encontrado: {payload.project_id}. Estado do Redis pode estar inconsistente.")
            raise HTTPException(status_code=404, detail=f"Sessão não encontrada para project_id: {payload.project_id}")
        analysis_type = getattr(session, "analysis_type", None)
        if payload.status in {"in_progress", "done"}:
            if not payload.report_data or not isinstance(payload.report_data, dict) or len(payload.report_data) != 1:
                logger.error(f"Webhook com report_data inválido para project_id {payload.project_id}")
                raise HTTPException(status_code=400, detail="report_data deve ser um dicionário com exatamente uma chave de relatório.")
            if not validate_report_data_structure(payload.report_data, analysis_type):
                logger.error(f"Estrutura de report_data inválida para analysis_type '{analysis_type}' e project_id '{payload.project_id}'")
                raise HTTPException(status_code=400, detail=f"Estrutura de report_data inválida para analysis_type '{analysis_type}'")
            report_field = list(payload.report_data.keys())[0]
            report_value = payload.report_data[report_field]
            session_dict = session.dict()
            session_dict[report_field] = report_value
            redis_service.update_report(payload.project_id, payload.report_data)
            logger.info(f"Relatório atualizado para sessão (project_id={payload.project_id}, nome_projeto={session.nome_projeto})")
            await ProjectStateService.save_state_to_blob(session)
        elif payload.status == "error":
            logger.error(f"Webhook de erro recebido: job_id={payload.job_id}, error_type={payload.error_type}, error_message={payload.error_message}")
        return {"status": "ok", "project_id": payload.project_id, "nome_projeto": session.nome_projeto}
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        logger.error(f"Erro ao processar webhook MCP: {exc}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar webhook MCP.")
