from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import JSONResponse
from backend.app.services.redis_session_service import RedisSessionService
from backend.app.services.mcp_client_service import MCPClientService
from backend.app.core.config import settings
import logging
import json

router = APIRouter()
logger = logging.getLogger("session_api")

@router.get("/project/{project_id}/{job_id}/reports")
async def get_project_reports(
    project_id: str,
    job_id: str,
    email: str = Query(..., description="Email do usuário"),
    empresa: str = Query(..., description="Empresa do usuário")
):
    logger.info(f"[Session] Requisição: project_id={project_id}, job_id={job_id}, email={email}, empresa={empresa}")

    # 1. VALIDAÇÕES BÁSICAS DE ENTRADA
    if not project_id or not isinstance(project_id, str) or not project_id.strip():
        logger.error(f"[Session] project_id inválido ou ausente: {project_id}")
        raise HTTPException(status_code=400, detail="project_id inválido ou ausente.")
        
    if not job_id or not isinstance(job_id, str) or not job_id.strip():
        logger.error(f"[Session] job_id inválido ou ausente: {job_id}")
        raise HTTPException(status_code=400, detail="job_id inválido ou ausente.")

    redis_service = RedisSessionService()
    
    # 2. BUSCAR METADADOS DO JOB NO REDIS (Apenas dados de controle, super leve)
    logger.info(f"[Session] Buscando metadados do job no Redis para job_id={job_id}")
    job = await redis_service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado.")

    # 3. VALIDAÇÃO DE OWNERSHIP (Segurança Multi-tenant - Nível Empresa)
    if job.empresa and job.empresa != empresa:
        logger.error(f"[Session] ACESSO NEGADO: {email} ({empresa}) tentou ler job de {job.empresa}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Acesso negado: Este relatório pertence a outra organização."
        )

    # 4. VALIDAÇÃO DE PERMISSÃO (Segurança RBAC - Nível Usuário/Projeto)
    logger.info(f"[Session] Verificando permissões do usuário {email} para o projeto {project_id}")
    user_perms = await redis_service.get_user_permissions(email=email, company_id=empresa)
    
    # 4.1 Verifica se o usuário tem acesso ao projeto
    if not user_perms or project_id not in user_perms.get("project_permissions", {}):
        logger.error(f"[Session] ACESSO NEGADO: {email} não tem role vinculada ao projeto {project_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Acesso negado: Você não é membro (owner, editor ou viewer) deste projeto."
        )

    # 4.2 Verifica se o usuário tem acesso ao agente específico deste job
    agentes_permitidos = user_perms.get("allowed_agents", [])
    if job.analysis_type not in agentes_permitidos:
        logger.error(f"[Session] ACESSO NEGADO: {email} não tem permissão para o agente {job.analysis_type}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail=f"Acesso negado: Seu perfil não tem permissão para acessar relatórios do agente '{job.analysis_type}'."
        )

    # 5. VERIFICAR STATUS DO PROCESSAMENTO
    if job.status == 'error':
        error_msg = await redis_service.get_error_message_for_job(job_id)
        return JSONResponse(
            content={"status": "error", "message": error_msg, "job_id": job_id},
            status_code=status.HTTP_200_OK
        )
        
    if job.status in ['pending', 'processing']:
        logger.info(f"[Session] Job {job_id} ainda em processamento.")
        return JSONResponse(
            content={
                "status": "processing",
                "job_id": job_id,
                "project_id": project_id,
                "message": "O relatório ainda está sendo processado pelo MCP."
            },
            status_code=status.HTTP_202_ACCEPTED
        )

    # 6. JOB CONCLUÍDO: DELEGAR LEITURA PARA O MCP
    logger.info(f"[Session] Job {job_id} concluído. Solicitando relatório ao MCP...")
    
    # Busca dinamicamente qual a URL do App Service que tem o agente que fez esse job
    agents_config = getattr(settings, 'agents', getattr(settings, 'AGENTS', {}))
    if isinstance(agents_config, str):
        try:
            agents_config = json.loads(agents_config)
        except Exception:
            agents_config = {}
            
    agente_info = agents_config.get(job.analysis_type, {})
    mcp_url = agente_info.get("mcp_service_url", getattr(settings, 'MCP_SERVER_BASE_URL', ''))

    if not mcp_url:
        logger.error(f"[Session] Não foi possível determinar a URL do MCP para o tipo: {job.analysis_type}")
        raise HTTPException(status_code=500, detail="Configuração de URL do MCP ausente.")

    mcp_client = MCPClientService()
    
    try:
        # Repassa a chamada para o MCP (que vai ler do Blob Storage)
        report_data = await mcp_client.get_report(
            project_id=project_id, 
            job_id=job_id, 
            mcp_url=mcp_url
        )
        
        logger.info(f"[Session] Sucesso: Relatório recuperado do MCP e pronto para envio.")
        return JSONResponse(
            content={
                "report_data": report_data, 
                "job_id": job_id,
                "project_id": project_id,
                "status": "success"
            },
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"[Session] Erro ao buscar relatório no MCP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, 
            detail="Falha ao obter o relatório do serviço de agentes (MCP)."
        )
