import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from backend.app.middleware.auth_middleware import get_current_user, _extract_usuario_executor
from backend.app.services.project_state_service import ProjectStateService
from backend.app.models.project_models import ProjectListItem

router = APIRouter()
logger = logging.getLogger("projects_api")

@router.get("/check", tags=["Projects"])
async def check_project(
    nome_projeto: str = Query(..., description="Nome do projeto a ser verificado"),
    current_user: dict = Depends(get_current_user)
):
    usuario_executor = _extract_usuario_executor(current_user)
    logger.info(f"[CHECK] Verificando existência do projeto '{nome_projeto}' para usuario_executor='{usuario_executor}'")
    try:
        project_id = await ProjectStateService._get_project_id_by_name(usuario_executor, nome_projeto)
        logger.info(f"[CHECK] Resultado _get_project_id_by_name: {project_id}")
        if not project_id:
            logger.warning(f"[CHECK] Nenhum project_id encontrado para nome_projeto='{nome_projeto}' e usuario_executor='{usuario_executor}'. Verificando estados de resumo no Blob Storage...")
            latest_state = await ProjectStateService.load_latest_state_from_blob(usuario_executor, nome_projeto=nome_projeto)
            if latest_state and latest_state.get("project_id"):
                project_id = latest_state.get("project_id")
                logger.info(f"[CHECK] Fallback encontrou project_id='{project_id}' via load_latest_state_from_blob")
            else:
                _, container_client = ProjectStateService._get_blob_clients()
                prefix = f"{usuario_executor}/{nome_projeto}/estados/resumo/"
                blobs = list(container_client.list_blobs(name_starts_with=prefix))
                for blob in blobs:
                    if blob.name.endswith('.json'):
                        blob_client = container_client.get_blob_client(blob.name)
                        state_bytes = blob_client.download_blob().readall()
                        import json
                        state = json.loads(state_bytes.decode("utf-8"))
                        pid = state.get("project_id")
                        logger.warning(f"[CHECK] Estado encontrado: {blob.name}, project_id={pid}")
                return {"exists": False}
        state = await ProjectStateService.load_all_states_from_blob(usuario_executor, project_id=project_id)
        logger.info(f"[CHECK] Resultado load_all_states_from_blob: {bool(state)} para project_id={project_id}")
        if state:
            report_fields = [
                "epicos",
                "features",
                "times_descricao",
                "alocacao_times",
                "premissas_riscos"
            ]
            for field in report_fields:
                if state.get(field) is None:
                    state[field] = None
                else:
                    report_key = field + "_report"
                    if report_key in state[field] and (state[field][report_key] is None or not isinstance(state[field][report_key], list)):
                        state[field][report_key] = []
            if state.get("resumo") and "project_id" not in state["resumo"]:
                logger.error(f"[CHECK] Estado de resumo encontrado para '{nome_projeto}' mas project_id está ausente. Estado inválido ignorado.")
                return {"exists": False}
            if state.get("resumo") and "nome_projeto" not in state["resumo"]:
                state["resumo"]["nome_projeto"] = nome_projeto
            response = {"exists": True, "state": state}
            logger.info(f"[CHECK] Projeto '{nome_projeto}' encontrado para usuario_executor='{usuario_executor}' com project_id válido.")
            return response
        else:
            logger.info(f"Projeto '{nome_projeto}' NÃO encontrado para usuario_executor='{usuario_executor}'.")
            return {"exists": False}
    except Exception as e:
        logger.error(f"Erro ao buscar estado do projeto '{nome_projeto}' para usuario_executor='{usuario_executor}': {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao buscar estado do projeto: {str(e)}")

@router.get("/list", response_model=List[ProjectListItem], tags=["Projects"])
async def list_projects(current_user: dict = Depends(get_current_user)):
    usuario_executor = _extract_usuario_executor(current_user)
    projects = await ProjectStateService._fetch_and_sanitize_projects(usuario_executor)
    projetos_validos = []
    for p in projects:
        if not p.get("project_id") or not isinstance(p.get("project_id"), str) or not p.get("project_id").strip():
            logger.warning(f"[LIST] Projeto ignorado por ausência de project_id: {p}")
            continue
        if "nome_projeto" not in p:
            p["nome_projeto"] = p.get("nome_projeto", "")
        p.pop("projeto", None)
        p.pop("comentario_usuario", None)
        p.pop("docx_blob_url", None)
        if "ultima_analysis_type" not in p and "analysis_type" in p:
            p["ultima_analysis_type"] = p["analysis_type"]
            p.pop("analysis_type", None)
        if "analysis_type" in p:
            p.pop("analysis_type", None)
        projetos_validos.append(p)
    logger.info(f"[LIST] Total de projetos válidos retornados: {len(projetos_validos)}")
    return projetos_validos
