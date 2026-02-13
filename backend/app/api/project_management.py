
from fastapi import APIRouter, HTTPException, Body, status
from backend.app.services.mongodb_service import MongoDBService
from backend.app.services.permission_service import PermissionService
import logging

router = APIRouter()
logger = logging.getLogger("project_management_api")

class DeleteProjectRequest:
    def __init__(self, requester_email: str):
        self.requester_email = requester_email

@router.delete("/projects/{project_id}", tags=["Project Management"])
async def delete_project(
    project_id: str,
    body: dict = Body(...)
):
    requester_email = body.get("requester_email")
    if not requester_email:
        logger.error(f"[ProjectManagement] requester_email ausente no body para exclusão de projeto: project_id={project_id}")
        raise HTTPException(status_code=400, detail="Campo 'requester_email' é obrigatório.")
    mongo_service = MongoDBService()
    permission_service = PermissionService(mongo_service)
    # Validação de permissão: precisa ser owner para deletar
    try:
        has_permission, member_role, error_msg = await permission_service.check_user_project_action_permission(
            requester_email, project_id, action_type="delete_project"
        )
        logger.info(f"[ProjectManagement] Validação de permissão para exclusão: status={'success' if has_permission else 'fail'}, detalhes={error_msg if not has_permission else 'Permissão validada para exclusão.'}")
        if not has_permission:
            raise HTTPException(status_code=403, detail=error_msg or "Usuário não possui permissão para excluir este projeto.")
    except HTTPException as exc:
        logger.error(f"[ProjectManagement] Falha na validação de permissão para exclusão: {exc.detail}")
        return {"success": False, "message": exc.detail}
    except Exception as e:
        logger.error(f"[ProjectManagement] Erro ao validar permissão para exclusão: {e}")
        return {"success": False, "message": "Erro ao validar permissão para exclusão."}
    # Deletar o projeto
    try:
        result = await mongo_service.db.projects.delete_one({"_id": project_id})
        if result.deleted_count == 1:
            logger.info(f"[ProjectManagement] Projeto excluído com sucesso: project_id={project_id}")
            return {"success": True, "message": "Projeto excluído com sucesso."}
        else:
            logger.error(f"[ProjectManagement] Falha ao excluir projeto: project_id={project_id}")
            return {"success": False, "message": "Falha ao excluir projeto."}
    except Exception as e:
        logger.error(f"[ProjectManagement] Erro ao excluir projeto: {e}")
        return {"success": False, "message": f"Erro ao excluir projeto: {e}"}
