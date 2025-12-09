import logging
from fastapi import APIRouter, HTTPException, status, Request
from backend.app.models.mcp_webhook_models import MCPWebhookPayload
from backend.app.services.redis_session_service import RedisSessionService
from backend.app.services.project_state_service import ProjectStateService
from backend.app.config.analysis_type_to_report_mapping import analysis_type_to_report_mapping

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
        project_id = payload.project_id
        if payload.status == "in_progress":
            logger.info(f"Webhook MCP status 'in_progress' recebido para project_id {project_id}. Nenhuma atualização de estado será feita.")
            resumo_state = redis_service.get_resumo_state(project_id)
            return {"status": "ok", "project_id": project_id, "nome_projeto": resumo_state.get("nome_projeto") if resumo_state else None}
        elif payload.status == "done":
            analysis_type = payload.analysis_type if hasattr(payload, 'analysis_type') else None
            if not analysis_type:
                # Tenta inferir pelo report_data
                report_data = payload.report_data or {}
                if report_data:
                    for k in report_data.keys():
                        for atype, rtype in analysis_type_to_report_mapping.items():
                            if rtype == k:
                                analysis_type = atype
                                break
            report_data = payload.report_data
            if not report_data or not isinstance(report_data, dict) or len(report_data) != 1:
                logger.error(f"Estrutura de report_data inválida para project_id '{project_id}'")
                raise HTTPException(status_code=400, detail=f"Estrutura de report_data inválida")
            report_field = list(report_data.keys())[0]
            report_type = report_field
            # Carrega estado anterior do report
            prev_state = redis_service.get_report_state(project_id, report_type)
            resumo_state = redis_service.get_resumo_state(project_id)
            now = datetime.utcnow().isoformat()
            state_data = {
                "nome_projeto": resumo_state.get("nome_projeto") if resumo_state else None,
                "ultima_analysis_type": analysis_type,
                "created_at": resumo_state.get("created_at") if resumo_state else now,
                "ultima_atualizacao": now,
                report_type: report_data[report_type]
            }
            redis_service.update_report_state(project_id, report_type, state_data)
            await ProjectStateService.save_state_to_blob(state_data, report_type=report_type)
            # Atualiza resumo do projeto
            if resumo_state:
                resumo_state["ultima_analysis_type"] = analysis_type
                resumo_state["ultima_atualizacao"] = now
                redis_service.restore_session_from_state(
                    usuario_executor=resumo_state.get("usuario_executor", None),
                    nome_projeto=resumo_state.get("nome_projeto", None),
                    analysis_type=analysis_type,
                    project_state=resumo_state
                )
            return {"status": "ok", "project_id": project_id, "nome_projeto": resumo_state.get("nome_projeto") if resumo_state else None, "state": state_data}
        elif payload.status == "error":
            resumo_state = redis_service.get_resumo_state(project_id)
            logger.error(f"Webhook de erro recebido: job_id={payload.job_id}, error_type={payload.error_type}, error_message={payload.error_message}")
            return {"status": "ok", "project_id": project_id, "nome_projeto": resumo_state.get("nome_projeto") if resumo_state else None}
        resumo_state = redis_service.get_resumo_state(project_id)
        return {"status": "ok", "project_id": project_id, "nome_projeto": resumo_state.get("nome_projeto") if resumo_state else None}
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        logger.error(f"Erro ao processar webhook MCP: {exc}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar webhook MCP.")
