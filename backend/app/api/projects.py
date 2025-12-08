import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import List
from backend.app.middleware.auth_middleware import get_current_user, _extract_usuario_executor
from backend.app.services.project_state_service import ProjectStateService
from backend.app.models.project_models import ProjectListItem
from backend.app.services.audit_service import AuditService

router = APIRouter()
logger = logging.getLogger("projects_api")

@router.get("/check", tags=["Projects"])
async def check_project(
    nome_projeto: str = Query(..., description="Nome do projeto a ser verificado"),
    current_user: dict = Depends(get_current_user),
    request: Request = None
):
    usuario_executor = _extract_usuario_executor(current_user)
    try:
        if request is not None:
            try:
                payload_dict = dict(request.query_params)
                AuditService.save_frontend_to_backend_payload(
                    payload=payload_dict,
                    endpoint="/projects/check",
                    method="GET",
                    usuario_executor=usuario_executor,
                    project_id=None
                )
            except Exception as e:
                logger.error(f"Erro ao auditar payload frontend->backend em /projects/check: {e}")
        logger.info(f"Verificando existência do projeto '{nome_projeto}' para usuario_executor='{usuario_executor}'")
        project_id = await ProjectStateService._get_project_id_by_name(usuario_executor, nome_projeto)
        if not project_id:
            logger.info(f"Projeto '{nome_projeto}' NÃO encontrado para usuario_executor='{usuario_executor}'.")
            response = {"exists": False}
            try:
                AuditService.save_backend_to_frontend_payload(
                    response=response,
                    endpoint="/projects/check",
                    status_code=200,
                    usuario_executor=usuario_executor,
                    project_id=None
                )
            except Exception as e:
                logger.error(f"Erro ao auditar payload backend->frontend em /projects/check: {e}")
            return response
        state = await ProjectStateService.load_latest_state_from_blob(usuario_executor, project_id=project_id)
        if state:
            state.pop("projeto", None)
            state.pop("comentario_usuario", None)
            state.pop("docx_blob_url", None)
            report_fields = [
                "epicos_report",
                "features_report",
                "times_descricao_report",
                "alocacao_times_report",
                "premissas_riscos_report"
            ]
            normalized_count = 0
            for field in report_fields:
                if field not in state or state[field] is None or not isinstance(state[field], list):
                    state[field] = []
                    normalized_count += 1
            if normalized_count > 0:
                logger.debug(f"Normalização: {normalized_count} campos de relatório convertidos para lista em check_project().")
            state["project_id"] = project_id
            state["nome_projeto"] = state.get("nome_projeto", nome_projeto)
            response = {"exists": True, "state": state}
            try:
                AuditService.save_backend_to_frontend_payload(
                    response=response,
                    endpoint="/projects/check",
                    status_code=200,
                    usuario_executor=usuario_executor,
                    project_id=project_id
                )
            except Exception as e:
                logger.error(f"Erro ao auditar payload backend->frontend em /projects/check: {e}")
            return response
        else:
            logger.info(f"Projeto '{nome_projeto}' NÃO encontrado para usuario_executor='{usuario_executor}'.")
            response = {"exists": False}
            try:
                AuditService.save_backend_to_frontend_payload(
                    response=response,
                    endpoint="/projects/check",
                    status_code=200,
                    usuario_executor=usuario_executor,
                    project_id=None
                )
            except Exception as e:
                logger.error(f"Erro ao auditar payload backend->frontend em /projects/check: {e}")
            return response
    except Exception as e:
        logger.error(f"Erro ao buscar estado do projeto '{nome_projeto}' para usuario_executor='{usuario_executor}': {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao buscar estado do projeto: {str(e)}")

@router.get("/list", response_model=List[ProjectListItem], tags=["Projects"])
async def list_projects(current_user: dict = Depends(get_current_user), request: Request = None):
    usuario_executor = _extract_usuario_executor(current_user)
    try:
        if request is not None:
            try:
                AuditService.save_frontend_to_backend_payload(
                    payload={},
                    endpoint="/projects/list",
                    method="GET",
                    usuario_executor=usuario_executor,
                    project_id=None
                )
            except Exception as e:
                logger.error(f"Erro ao auditar payload frontend->backend em /projects/list: {e}")
        projects = await ProjectStateService._fetch_and_sanitize_projects(usuario_executor)
        for p in projects:
            if "nome_projeto" not in p:
                p["nome_projeto"] = p.get("nome_projeto", "")
            p.pop("projeto", None)
            p.pop("comentario_usuario", None)
            p.pop("docx_blob_url", None)
        try:
            AuditService.save_backend_to_frontend_payload(
                response=projects,
                endpoint="/projects/list",
                status_code=200,
                usuario_executor=usuario_executor,
                project_id=None
            )
        except Exception as e:
            logger.error(f"Erro ao auditar payload backend->frontend em /projects/list: {e}")
        return projects
    except Exception as e:
        logger.error(f"Erro ao listar projetos do usuário {usuario_executor}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar projetos: {str(e)}")
