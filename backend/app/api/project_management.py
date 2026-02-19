import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Body, Depends, status

from backend.app.services.mongodb_service import MongoDBService
from backend.app.services.permission_service import PermissionService
from backend.app.models.project_management_models import (
    ListOwnedProjectsResponse,
    ProjectWithRoleItem,
    OwnedProjectItem,
    AddProjectMemberRequest,
    AddProjectMemberResponse,
    UpdateProjectMembersRequest,
    UpdateProjectMembersResponse,
    DeleteProjectRequest,
    DeleteProjectResponse
)
from backend.app.services.redis_session_service import RedisSessionService

router = APIRouter()
logger = logging.getLogger("project_management_api")

# Helper para Injeção de Dependência
def get_mongo_service():
    return MongoDBService()

# --- Routes ---

@router.get("/list", response_model=List[ProjectWithRoleItem], tags=["Project Management"])
async def list_all_user_projects(
    email: str = Query(..., description="Email do usuário"),
    mongo_service: MongoDBService = Depends(get_mongo_service)
):
    """
    Lista TODOS os projetos que o usuário tem acesso.
    Retorna também o 'role' (nível de acesso) específico do usuário naquele projeto.
    """
    logger.info(f"[ProjectList] Buscando projetos para: {email}")
    
    projects = await mongo_service.get_user_projects_with_access(email)
    
    if not projects:
        return []
        
    return projects
    
@router.get("/owned", response_model=ListOwnedProjectsResponse, tags=["Project Management"])
async def list_owned_projects(
    email: str = Query(..., description="Email do usuário owner"),
    mongo_service: MongoDBService = Depends(get_mongo_service) # <--- O serviço entra aqui
):
    logger.info(f"[ProjectManagement] Recebida requisição para /projects/owned com email={email}")
    
    # REMOVIDO: mongo_service = MongoDBService()
    
    user = await mongo_service.get_user_by_email(email)
    if not user:
        logger.error(f"[ProjectManagement] Usuário não encontrado: email={email}")
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        
    company_id = getattr(user, "company_id", None)
    if not company_id:
        logger.error(f"[ProjectManagement] Usuário não possui company_id: email={email}")
        raise HTTPException(status_code=400, detail="Usuário não possui company_id.")
        
    projects = await mongo_service.get_projects_where_user_is_owner(email, company_id=company_id)
    
    items = [OwnedProjectItem(
        project_id=p["project_id"],
        name=p["name"],
        description=p.get("description"),
        members=p.get("members", [])
    ) for p in projects]
    
    return ListOwnedProjectsResponse(projects=items)

@router.post("/{project_id}/members", response_model=AddProjectMemberResponse, tags=["Project Management"])
async def add_project_member(
    project_id: str, 
    req: AddProjectMemberRequest = Body(...),
    mongo_service: MongoDBService = Depends(get_mongo_service) # <--- O serviço entra aqui
):
    logger.info(f"[ProjectManagement] Adicionar membro: project_id={project_id}, requester={req.requester_email}")
    
    # REMOVIDO: mongo_service = MongoDBService()
    
    permission_service = PermissionService(mongo_service)
    redis_session_service = RedisSessionService()
    
    try:
        # 1. Validação de permissão
        has_perm, _, error_msg = await permission_service.check_user_project_action_permission(
            req.requester_email, project_id, action_type="add_member"
        )
        if not has_perm:
            return AddProjectMemberResponse(success=False, message=error_msg or "Sem permissão.")
            
        # 2. Validação extra de Ownership (Opcional, pois check_user_project_action_permission já deve cobrir, mas mantemos por segurança)
        # Note: Precisamos instanciar o Helper de verify_user aqui se formos usar, ou mover a lógica para o service.
        # Como verify_user_is_owner é local, vamos usá-lo passando o serviço injetado:
        if not await _verify_user_is_owner_helper(req.requester_email, project_id, mongo_service):
             return AddProjectMemberResponse(success=False, message="Apenas Owners podem adicionar membros.")

        # 3. Busca novo membro
        new_user = await mongo_service.get_user_by_email(req.new_member_email)
        if not new_user:
            return AddProjectMemberResponse(success=False, message="Usuário a ser adicionado não encontrado.")
            
        new_member = {
            "user_id": str(new_user.id),
            "email": req.new_member_email,
            "role": req.role,
            "added_at": datetime.utcnow().isoformat()
        }
        
        result = await mongo_service.add_member_to_project(project_id, new_member)
        
        # Cache invalidation
        project = await mongo_service.get_project_by_id(project_id)
        if project:
            company_id = getattr(project, "company_id", None)
            # Invalida o cache do novo membro para que ele veja o projeto imediatamente
            redis_session_service.invalidate_user_permissions(req.new_member_email, company_id)
            
        return AddProjectMemberResponse(
            success=bool(result), 
            message="Membro adicionado!" if result else "Erro ao adicionar."
        )
    except Exception as e:
        logger.error(f"Erro add_project_member: {e}")
        return AddProjectMemberResponse(success=False, message=str(e))

@router.put("/{project_id}/members", response_model=UpdateProjectMembersResponse, tags=["Project Management"])
async def update_project_members(
    project_id: str, 
    req: UpdateProjectMembersRequest = Body(...),
    mongo_service: MongoDBService = Depends(get_mongo_service) # <--- O serviço entra aqui
):
    logger.info(f"[ProjectManagement] Atualizar membros: project_id={project_id}")
    
    # REMOVIDO: mongo_service = MongoDBService()
    
    permission_service = PermissionService(mongo_service)
    redis_session_service = RedisSessionService()
    
    try:
        # 1. Verifica permissão básica de edição
        has_perm, _, error_msg = await permission_service.check_user_project_action_permission(
            req.requester_email, project_id, action_type="edit_project"
        )
        if not has_perm:
            return UpdateProjectMembersResponse(success=False, message=error_msg)

        # 2. Verifica se quem pede é Owner
        if not await _verify_user_is_owner_helper(req.requester_email, project_id, mongo_service):
            return UpdateProjectMembersResponse(success=False, message="Apenas Owners podem gerenciar membros.")
        
        # Identifica os owners na NOVA lista que está chegando
        incoming_owners = [m for m in req.members if m.get("role", "").lower() == "owner"]
        
        # Regra 1: O projeto não pode ficar sem nenhum owner
        if not incoming_owners:
            return UpdateProjectMembersResponse(
                success=False, 
                message="Ação negada: A lista de membros deve conter pelo menos um Owner."
            )

        # Busca como o requisitante ficou na NOVA lista
        requester_in_new_list = next(
            (m for m in req.members if m.get("email") == req.requester_email), None
        )

        # Regra 2: O Owner não pode se remover via update
        if not requester_in_new_list:
             return UpdateProjectMembersResponse(
                success=False, 
                message="Você não pode se remover da lista via atualização. Use a função de sair do projeto."
            )

        # Regra 3: Se o requisitante está se rebaixando
        if requester_in_new_list.get("role", "").lower() != "owner":
            other_owners = [m for m in incoming_owners if m.get("email") != req.requester_email]
            if not other_owners:
                return UpdateProjectMembersResponse(
                    success=False, 
                    message="Você não pode alterar seu nível para Editor/Viewer sem antes promover outro membro a Owner."
                )
                
        # 3. Executa a atualização
        result = await mongo_service.update_project_members(project_id, req.members)
        
        # 4. Invalidação de Cache Inteligente
        # (O mongo_service já faz uma parte, mas aqui garantimos varredura completa se necessário)
        project = await mongo_service.get_project_by_id(project_id)
        if project:
            company_id = getattr(project, "company_id", None)
            affected_emails = [m.get("email") for m in req.members if m.get("email")]
            for email in set(affected_emails):
                redis_session_service.invalidate_user_permissions(email, company_id)

        return UpdateProjectMembersResponse(
            success=bool(result), 
            message="Membros atualizados com sucesso!" if result else "Falha na atualização."
        )

    except Exception as e:
        logger.error(f"Erro update_project_members: {e}")
        return UpdateProjectMembersResponse(success=False, message=str(e))

@router.delete("/{project_id}/members/{target_email}", tags=["Project Management"])
async def remove_project_member(
    project_id: str, 
    target_email: str, 
    requester_email: str = Query(..., description="Email de quem está solicitando a remoção"),
    mongo_service: MongoDBService = Depends(get_mongo_service) # <--- O serviço entra aqui
):
    logger.info(f"[ProjectManagement] Remove Member: project={project_id}, target={target_email}")
    
    # REMOVIDO: mongo_service = MongoDBService()
    
    permission_service = PermissionService(mongo_service)
    redis_session_service = RedisSessionService()
    
    # 1. Verifica Permissão
    has_perm, _, error_msg = await permission_service.check_user_project_action_permission(
        requester_email, project_id, action_type="remove_member"
    )
    if not has_perm:
        raise HTTPException(status_code=403, detail=error_msg)
    
    project = await mongo_service.get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    # 2. Validação: Não permitir remover o último owner
    target_member = next((m for m in project.members if m.email == target_email), None)
    if target_member and target_member.role.lower() == "owner":
        owners = [m for m in project.members if m.role.lower() == "owner"]
        if len(owners) <= 1:
            raise HTTPException(
                status_code=400, 
                detail="Não é possível remover o único dono do projeto. Adicione outro dono antes de remover este."
            )
            
    success = await mongo_service.remove_member_from_project(project_id, target_email)
    
    company_id = getattr(project, "company_id", None)
    # Cache Invalidation:
    # 1. Quem foi removido precisa atualizar
    redis_session_service.invalidate_user_permissions(target_email, company_id)
    # 2. Quem solicitou (se o frontend precisar atualizar a lista dele)
    redis_session_service.invalidate_user_permissions(requester_email, company_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Falha ao remover membro no banco de dados.")
        
    return {"success": True, "message": f"Membro {target_email} removido com sucesso."}

@router.delete("/{project_id}", response_model=DeleteProjectResponse, tags=["Project Management"])
async def delete_project(
    project_id: str, 
    req: DeleteProjectRequest = Body(...),
    mongo_service: MongoDBService = Depends(get_mongo_service) # <--- O serviço entra aqui
):
    """
    Remove permanentemente um projeto do banco de dados.
    """
    logger.info(f"[ProjectManagement] Tentativa de exclusão: project_id={project_id}, por={req.requester_email}")
    
    # REMOVIDO: mongo_service = MongoDBService()
    
    permission_service = PermissionService(mongo_service)
    redis_session_service = RedisSessionService()
    
    try:
        # 1. Verifica permissão de deletar
        has_permission, _, error_msg = await permission_service.check_user_project_action_permission(
            req.requester_email, project_id, action_type="delete_project"
        )
        if not has_permission:
            logger.warning(f"[ProjectManagement] Acesso negado para exclusão: {req.requester_email}")
            raise HTTPException(status_code=403, detail=error_msg or "Permissão negada.")
            
        # 2. Pega dados para limpar cache depois
        project = await mongo_service.get_project_by_id(project_id)
        if not project:
            return DeleteProjectResponse(success=False, message="Projeto não encontrado.")
            
        company_id = getattr(project, "company_id", None)
        affected_emails = [m.email for m in project.members] if project.members else []
        
        # 3. Deleta 
        success = await mongo_service.delete_project(project_id, company_id)

        # 4. Limpa Cache
        if success:
            for email in set(affected_emails):
                redis_session_service.invalidate_user_permissions(email, company_id)
            # Também invalida o do solicitante se ele não estava na lista (ex: admin)
            redis_session_service.invalidate_user_permissions(req.requester_email, company_id)
            
            logger.info(f"[ProjectManagement] Projeto {project_id} excluído com sucesso.")
            return DeleteProjectResponse(success=True, message="Projeto excluído com sucesso.")
            
        return DeleteProjectResponse(success=False, message="Erro ao excluir projeto ou projeto já excluído.")
        
    except HTTPException as hex:
        raise hex
    except Exception as e:
        logger.error(f"[ProjectManagement] Erro crítico na exclusão: {e}")
        return DeleteProjectResponse(success=False, message=f"Erro interno: {str(e)}")

# --- Helpers Locais (Renomeado para evitar conflito e ser interno) ---
async def _verify_user_is_owner_helper(email: str, project_id: str, mongo_service: MongoDBService) -> bool:
    project = await mongo_service.get_project_by_id(project_id)
    if not project:
        return False
    return any(m.email == email and m.role.lower() == "owner" for m in project.members)
