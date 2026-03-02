import json
import logging

from pathlib import Path
from types import SimpleNamespace
from fastapi.responses import JSONResponse
from fastapi import APIRouter, HTTPException, status, Query

from backend.app.services.redis_session_service import RedisSessionService
from backend.app.services.mcp_client_service import MCPClientService
from backend.app.services.mongodb_service import MongoDBService

from backend.app.api.utils import get_user_and_company_id
from backend.config.agent_mapping import AGENT_TO_CATEGORY
from backend.app.core.config import settings


router = APIRouter()
logger = logging.getLogger("session_api")

@router.get("/project/{project_id}/{job_id}/reports")
async def get_project_reports(
    project_id: str,
    job_id: str,
    email: str = Query(..., description="Email do usuário"),
):
    logger.info(f"[Session] Requisição recebida: project_id={project_id}, job_id={job_id}, email={email}")

    # 1. VALIDAÇÕES BÁSICAS DE ENTRADA
    if not project_id or not isinstance(project_id, str) or not project_id.strip():
        logger.error(f"[Session] project_id inválido ou ausente: {project_id}")
        raise HTTPException(status_code=400, detail="project_id inválido ou ausente.")
        
    if not job_id or not isinstance(job_id, str) or not job_id.strip():
        logger.error(f"[Session] job_id inválido ou ausente: {job_id}")
        raise HTTPException(status_code=400, detail="job_id inválido ou ausente.")

    # 2. DESCOBRINDO A EMPRESA
    mongo_service = MongoDBService()
    user, empresa = await get_user_and_company_id(email, mongo_service)
    
    # Aqui sim logamos a empresa, pois ela já foi carregada do banco!
    logger.info(f"[Session] Empresa resolvida automaticamente: {empresa}")

    redis_service = RedisSessionService()
    
    # 3. BUSCAR METADADOS DO JOB NO REDIS (Apenas dados de controle, super leve)
    logger.info(f"[Session] Buscando metadados do job no Redis para job_id={job_id}")
    job = await redis_service.get_job(job_id)

    if not job:
        logger.warning(f"[Session] Job {job_id} expirou no Redis. Buscando no histórico do MongoDB...")
        
        from backend.app.services.mongodb_service import MongoDBService
        mongo_service = MongoDBService()
        
        historico_job = await mongo_service.db.project_reports_history.find_one({"job_id": job_id})
        
        if historico_job:
            job = SimpleNamespace(
                status=historico_job.get("status", "done"),
                empresa=empresa,
                analysis_type=historico_job.get("analysis_type")
            )
            logger.info(f"[Session] Job {job_id} recuperado com sucesso do MongoDB!")
        else:
            raise HTTPException(status_code=404, detail="Job não encontrado nem em processamento, nem no histórico.")

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
    
    # ==========================================================
    # 🚀 FALLBACK 4.1: SE O REDIS NEGAR, VERIFICA NO MONGODB
    # ==========================================================
    is_member = False
    
    if user_perms and project_id in user_perms.get("project_permissions", {}):
        # Cenário Feliz: O Redis tinha a informação atualizada
        is_member = True
    else:
        # Fallback: O Redis negou (cache expirado ou projeto recém-criado)
        logger.warning(f"[Session] Permissão não achada no Redis para {email}. Buscando no MongoDB (Fallback)...")
        
        # Garante a importação e instanciação do serviço
        from backend.app.services.mongodb_service import MongoDBService
        mongo_service_fallback = MongoDBService()
        projeto_real = await mongo_service_fallback.get_project_by_id(project_id)
        
        if projeto_real:
            # Extrai a lista de membros (suporta dicionário do Mongo ou modelo do Pydantic)
            membros = getattr(projeto_real, "members", []) if not isinstance(projeto_real, dict) else projeto_real.get("members", [])
            # Verifica se o email do usuário está na lista
            is_member = any((getattr(m, "email", None) if not isinstance(m, dict) else m.get("email")) == email for m in membros)
            
        if not is_member:
            logger.error(f"[Session] ACESSO NEGADO DEFINITIVO: {email} não é membro do projeto {project_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Acesso negado: Você não é membro (owner, editor ou viewer) deste projeto."
            )
        else:
            logger.info(f"[Session] Permissão de {email} confirmada via MongoDB para o projeto recém-criado!")
            # Cria um "cache fantasma" local na memória só para não quebrar a validação 4.2 abaixo
            if not user_perms:
                user_perms = {"allowed_agents": [job.analysis_type]}
    # ==========================================================

    # 4.2 Verifica se o usuário tem acesso ao agente específico deste job
    agentes_permitidos = user_perms.get("allowed_agents", [])
    
    # Adicionamos um contorno seguro (and not is_member) caso o cache fantasma tenha sido usado
    if job.analysis_type not in agentes_permitidos and not is_member:
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
    
    # ==========================================================
    # 🚀 LÊ A URL DIRETO DO ARQUIVO mcp_agents.json
    # ==========================================================
    agents_config = {}
    try:
        # Resolve o caminho absoluto (sobe 3 pastas: api -> app -> backend -> entra em config)
        base_dir = Path(__file__).resolve().parent.parent.parent
        config_file_path = base_dir / "config" / "mcp_agents.json"
        
        if config_file_path.exists():
            with open(config_file_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)
                # O JSON tem a raiz "agents", então extraímos ela
                agents_config = json_data.get("agents", {})
        else:
            logger.warning(f"[Session] Arquivo não encontrado: {config_file_path}. Tentando fallback.")
            
    except Exception as e:
        logger.error(f"[Session] Erro ao ler mcp_agents.json: {e}")

    # Pega as informações específicas do agente que rodou este job
    agente_info = agents_config.get(job.analysis_type, {})
    mcp_url = agente_info.get("mcp_service_url")

    # Fallback final de segurança para variável de ambiente (caso o JSON falhe)
    if not mcp_url:
        mcp_url = getattr(settings, 'MCP_SERVER_BASE_URL', None)

    if not mcp_url:
        logger.error(f"[Session] Não foi possível determinar a URL do MCP para o tipo: {job.analysis_type}")
        raise HTTPException(status_code=500, detail="Configuração de URL do MCP ausente.")

    # ==========================================================
    # 🚀 FAZ A REQUISIÇÃO PARA O MCP (USANDO O SEU MAPPING)
    # ==========================================================
    mcp_client = MCPClientService()
    
    # 1. Busca a categoria exata no seu arquivo de configuração
    categoria = AGENT_TO_CATEGORY.get(job.analysis_type)
    
    # 2. Adiciona o .md no final (ou usa um fallback de segurança se esquecerem de mapear um agente novo)
    if categoria:
        nome_arquivo_dinamico = f"{categoria}.md"
    else:
        logger.warning(f"[Session] Agente '{job.analysis_type}' não mapeado em AGENT_TO_CATEGORY. Usando nome próprio.")
        nome_arquivo_dinamico = f"{job.analysis_type}.md"

    try:
        # Repassa a chamada para o MCP enviando o nome do arquivo montado perfeitamente
        report_data = await mcp_client.get_report(
            project_id=project_id, 
            job_id=job_id, 
            mcp_url=mcp_url,
            company_id=empresa, 
            filename=nome_arquivo_dinamico # 🚀 "epics.md", "features.md", etc.
        )
        
        logger.info(f"[Session] Sucesso: Arquivo {nome_arquivo_dinamico} recuperado do MCP.")
        
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
