import logging
from fastapi import APIRouter, HTTPException, status, Request, Depends
from backend.app.models.mcp_webhook_models import MCPWebhookPayload
from backend.app.services.redis_session_service import RedisSessionService
from backend.app.utils.webhook_validator import validate_report_data_structure
from backend.app.services.project_state_service import ProjectStateService

router = APIRouter()
logger = logging.getLogger("webhooks_api")

REPORT_FIELDS = [
    "epicos_report",
    "features_report",
    "times_descricao_report",
    "alocacao_times_report",
    "premissas_riscos_report"
]

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
        # Passo 7: Salva o estado dos campos de relatório antes da atualização
        state_before = {k: getattr(session, k, None) for k in REPORT_FIELDS}
        logger.info(f"[webhook] Estado dos campos de relatório ANTES da atualização: {state_before}")
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
                # Passo 6 e 7: Busca o estado após a atualização
                state_after = {k: getattr(session_atualizada, k, None) for k in REPORT_FIELDS}
                logger.info(f"[webhook] Estado dos campos de relatório DEPOIS da atualização: {state_after}")
                # Passo 6: Validação extra: todos os campos de relatório devem ser preservados
                for k in REPORT_FIELDS:
                    if k in state_before and state_before[k] is not None:
                        if getattr(session_atualizada, k, None) is None and k != f"{payload.report_type}_report":
                            logger.critical(f"Após update_report, o campo '{k}' foi perdido (estava presente antes). Estado atual: {[(kk, getattr(session_atualizada, kk, None)) for kk in REPORT_FIELDS]}")
                            raise HTTPException(status_code=500, detail=f"Campo de relatório '{k}' não foi preservado após atualização.")
                # Passo 8: Busca o estado anterior do Blob para comparar as chaves dos campos de relatório
                try:
                    state_anterior = await ProjectStateService.load_latest_state_from_blob(session.usuario_executor, session.projeto, session_id=session.session_id)
                except Exception as e:
                    logger.error(f"Erro ao buscar estado anterior do Blob: {e}")
                    state_anterior = None
                chaves_anteriores = set()
                if state_anterior:
                    for k in REPORT_FIELDS:
                        if state_anterior.get(k) is not None:
                            chaves_anteriores.add(k)
                chaves_atuais = set()
                for k in REPORT_FIELDS:
                    if getattr(session_atualizada, k, None) is not None:
                        chaves_atuais.add(k)
                chaves_perdidas = chaves_anteriores - chaves_atuais
                if chaves_perdidas:
                    logger.critical(f"Após update_report, as chaves {chaves_perdidas} não foram preservadas em reports para session_id={session.session_id}. Chaves atuais: {list(chaves_atuais)}")
                    raise HTTPException(status_code=500, detail=f"Chaves {chaves_perdidas} não encontradas em reports após atualização.")
                logger.info(f"Validação pós-update_report: todos os campos de relatório preservados. Chaves atuais: {list(chaves_atuais)}")
            except Exception as e:
                logger.critical(f"Erro crítico ao validar integridade dos campos de relatório após update_report: {e}")
                raise HTTPException(status_code=500, detail=f"Erro ao validar integridade dos campos de relatório: {e}")
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
