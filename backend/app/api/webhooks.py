import logging
from datetime import datetime # <--- Import necessário
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
        
        # 1. Recupera a sessão (Isso aqui é o "Enrichment" - traz o nome_projeto do Redis)
        session = redis_service.get_session_by_project_id(payload.project_id)
        
        if not session:
            logger.error(f"Webhook recebido para project_id não encontrado: {payload.project_id}. Estado do Redis pode estar inconsistente.")
            raise HTTPException(status_code=404, detail=f"Sessão não encontrada para project_id: {payload.project_id}")
            
        if payload.status == "in_progress":
            logger.info(f"Webhook MCP status 'in_progress' recebido para project_id {payload.project_id}. Nenhuma atualização de estado será feita.")
            return {"status": "ok", "project_id": payload.project_id, "nome_projeto": session.nome_projeto}
            
        elif payload.status == "done":
            import json
            logger.info(f"🔍 [DEBUG WEBHOOK] Conteúdo recebido do MCP: {json.dumps(payload.report_data)}")
            report_data = payload.report_data
            if not report_data or not isinstance(report_data, dict) or len(report_data) != 1:
                logger.error(f"Estrutura de report_data inválida para project_id '{payload.project_id}'")
                raise HTTPException(status_code=400, detail=f"Estrutura de report_data inválida")
            
            report_field = list(report_data.keys())[0]
            
            # Inicializa lista se não existir (Defensivo)
            if not hasattr(session, report_field) or getattr(session, report_field) is None:
                logger.warning(f"Campo de relatório '{report_field}' não existia ou estava None para project_id '{payload.project_id}'. Inicializando como lista vazia.")
                setattr(session, report_field, [])
            
            valor_anterior = getattr(session, report_field)
            
            # 2. Atualiza o dado no Redis
            redis_service.update_report(payload.project_id, report_data)
            logger.info(f"Campo de relatório '{report_field}' atualizado via webhook para project_id {payload.project_id}. Valor anterior: {valor_anterior}")
            
            # 3. Recupera a sessão atualizada
            session = redis_service.get_session_by_project_id(payload.project_id)
            
            # --- CORREÇÃO APLICADA AQUI ---
            # O Redis Session Service pode retornar um objeto customizado. 
            # Precisamos garantir que 'ultima_atualizacao' seja atualizado agora,
            # pois o ProjectStateService.save_state_to_blob vai validar isso.
            
            agora = datetime.utcnow() # timestamp atual
            
            # Se a sessão for um objeto Pydantic ou classe, atualizamos o atributo
            if hasattr(session, "ultima_atualizacao"):
                session.ultima_atualizacao = agora
            # Se for um dicionário (depende da sua implementação do Redis Service), atualizamos a chave
            elif isinstance(session, dict):
                session["ultima_atualizacao"] = agora.isoformat()

            # Garantimos que o project_id está explícito na sessão antes de salvar
            if hasattr(session, "project_id") and not session.project_id:
                session.project_id = payload.project_id
            
            # 4. Salva no Blob Storage (Agora o 'session' está completo e atualizado)
            await ProjectStateService.save_state_to_blob(session)
            
            # Prepara retorno
            state = session.to_project_state() if hasattr(session, "to_project_state") else session
            
            return {
                "status": "ok", 
                "project_id": payload.project_id, 
                "nome_projeto": getattr(session, "nome_projeto", "Desconhecido"), # Safe get
                "state": state
            }
            
        elif payload.status == "error":
            logger.error(f"Webhook de erro recebido: job_id={payload.job_id}, error_type={payload.error_type}, error_message={payload.error_message}")
            return {"status": "ok", "project_id": payload.project_id, "nome_projeto": getattr(session, "nome_projeto", "Desconhecido")}
            
        return {"status": "ok", "project_id": payload.project_id, "nome_projeto": getattr(session, "nome_projeto", "Desconhecido")}
        
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        logger.error(f"Erro ao processar webhook MCP: {exc}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar webhook MCP.")
