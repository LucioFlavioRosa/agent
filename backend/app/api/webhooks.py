import logging
from fastapi import APIRouter, HTTPException, status, Request, Depends
from backend.app.models.mcp_webhook_models import MCPWebhookPayload
from backend.app.services.redis_session_service import RedisSessionService
from backend.app.utils.webhook_validator import validate_report_data_structure
from backend.app.services.project_state_service import ProjectStateService

router = APIRouter()
logger = logging.getLogger("webhooks_api")

@router.post("/mcp", status_code=200, tags=["Webhooks"])
async def mcp_webhook(payload: MCPWebhookPayload, request: Request):
    redis_service = RedisSessionService()
    logger.info(f"Recebido webhook MCP para session_id: {payload.session_id}, status: {payload.status}")
    session = None
    try:
        logger.info(f"Buscando sessão associada ao session_id: {payload.session_id}")
        try:
            session = redis_service.get_session(payload.session_id)
        except Exception as e:
            logger.error(f"Sessão não encontrada no Redis para session_id={payload.session_id}: {e}")
            usuario_executor = getattr(payload, "usuario_executor", None)
            projeto = getattr(payload, "projeto", None)
            state = None
            if usuario_executor and projeto:
                logger.info(f"Tentando buscar estado no Blob Storage via usuario_executor={usuario_executor}, projeto={projeto}")
                try:
                    state = await ProjectStateService.load_latest_state_from_blob(usuario_executor, projeto, session_id=payload.session_id)
                except Exception as ex_blob:
                    logger.error(f"Erro ao buscar estado no Blob Storage via usuario_executor/projeto: {ex_blob}")
            if not state:
                logger.info(f"Tentando buscar estado no Blob Storage via session_id={payload.session_id}")
                try:
                    state = await ProjectStateService.load_latest_state_by_session_id(payload.session_id)
                except Exception as ex_blob2:
                    logger.error(f"Erro ao buscar estado no Blob Storage via session_id: {ex_blob2}")
            if state:
                usuario_executor_restore = state.get("usuario_executor")
                projeto_restore = state.get("projeto")
                analysis_type_restore = state.get("analysis_type")
                logger.info(f"Restaurando sessão no Redis para session_id={payload.session_id}, usuario_executor={usuario_executor_restore}, projeto={projeto_restore}, analysis_type={analysis_type_restore}")
                redis_service.restore_session_from_state(
                    usuario_executor_restore,
                    projeto_restore,
                    analysis_type_restore,
                    state,
                    session_id=payload.session_id
                )
                try:
                    session = redis_service.get_session(payload.session_id)
                    logger.info(f"Sessão restaurada no Redis para session_id={payload.session_id}")
                except Exception as e2:
                    logger.error(f"Falha ao recuperar sessão restaurada do Redis: {e2}")
                    session = None
            else:
                logger.error(f"Webhook recebido para session_id não encontrado: {payload.session_id}. Estado do Redis e Blob Storage podem estar inconsistentes.")
                raise HTTPException(status_code=404, detail=f"Sessão não encontrada para session_id: {payload.session_id}")
        analysis_type = getattr(session, "analysis_type", None)
        if payload.status in {"in_progress", "done"}:
            if not payload.report_type:
                logger.error(f"Webhook sem report_type para session_id {payload.session_id}")
                raise HTTPException(status_code=400, detail="report_type é obrigatório quando status é 'in_progress' ou 'done'")
            if not validate_report_data_structure(payload.report_type, payload.report_data, analysis_type):
                logger.error(f"Estrutura de report_data inválida para report_type '{payload.report_type}', analysis_type '{analysis_type}' e session_id '{payload.session_id}'")
                raise HTTPException(status_code=400, detail=f"Estrutura de report_data inválida para report_type '{payload.report_type}' e analysis_type '{analysis_type}'")
            logger.info(f"Atualizando relatório '{payload.report_type}' na sessão {session.session_id} via substituição total da chave no dicionário reports.")
            await redis_service.update_report(
                session.session_id,
                payload.report_type,
                payload.report_data,
                analysis_type=analysis_type
            )
            try:
                session_atualizada = redis_service.get_session(session.session_id)
                reports_dict = getattr(session_atualizada, 'reports', {})
                if not isinstance(reports_dict, dict):
                    logger.critical(f"Após update_report, reports não é um dicionário para session_id={session.session_id}")
                    raise HTTPException(status_code=500, detail="Campo 'reports' corrompido após atualização.")
                if payload.report_type not in reports_dict and not any(payload.report_type in k for k in reports_dict.keys()):
                    logger.critical(f"Após update_report, chave '{payload.report_type}' não encontrada em reports para session_id={session.session_id}. Chaves atuais: {list(reports_dict.keys())}")
                    raise HTTPException(status_code=500, detail=f"Chave '{payload.report_type}' não encontrada em reports após atualização.")
                logger.info(f"Validação pós-update_report: reports contém as chaves: {list(reports_dict.keys())}")
                # Validação de integridade: garantir que todas as chaves anteriores foram preservadas
                # Busca o estado anterior do Blob para comparar as chaves
                try:
                    state_anterior = await ProjectStateService.load_latest_state_from_blob(session.usuario_executor, session.projeto, session_id=session.session_id)
                    if state_anterior and 'reports' in state_anterior:
                        chaves_anteriores = set(state_anterior['reports'].keys())
                        chaves_atuais = set(reports_dict.keys())
                        chaves_perdidas = chaves_anteriores - chaves_atuais
                        if chaves_perdidas:
                            logger.critical(f"Após update_report, as chaves {chaves_perdidas} não foram preservadas em reports para session_id={session.session_id}. Chaves atuais: {list(reports_dict.keys())}")
                            raise HTTPException(status_code=500, detail=f"Chaves {chaves_perdidas} não encontradas em reports após atualização.")
                except Exception as e:
                    logger.error(f"Erro ao validar integridade das chaves de reports após update_report: {e}")
            except Exception as e:
                logger.critical(f"Erro crítico ao validar integridade de reports após update_report: {e}")
                raise HTTPException(status_code=500, detail=f"Erro ao validar integridade de reports: {e}")
            try:
                await ProjectStateService.save_state_to_blob(session_atualizada)
                logger.info(f"Estado salvo imediatamente após atualização de relatório para sessão {session.session_id} (session_id={payload.session_id})")
            except Exception as e:
                logger.error(f"Erro ao salvar estado imediato no Blob após webhook MCP: {e}")
            logger.info(f"Relatório '{payload.report_type}' atualizado para sessão {session.session_id} (session_id={payload.session_id})")
        elif payload.status == "error":
            logger.error(f"Webhook de erro recebido: session_id={payload.session_id}, error_type={payload.error_type}, error_message={payload.error_message}")
        return {"status": "ok"}
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        logger.error(f"Erro ao processar webhook MCP: {exc}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar webhook MCP.")
