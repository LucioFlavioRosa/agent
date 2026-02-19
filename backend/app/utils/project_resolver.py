from fastapi import HTTPException
from backend.app.utils.string_utils import normalize_string_general
from backend.app.services.mongodb_service import MongoDBService

async def resolve_project_id_by_name(project_name: str, company_id: str, mongo_service: MongoDBService) -> str:
    """
    Resolve o project_id a partir do nome do projeto e company_id.
    1. Normaliza o nome do projeto.
    2. Busca o projeto pelo nome normalizado e company_id.
    3. Retorna o project_id se encontrado, ou lança HTTPException(404) caso contrário.
    """
    if not project_name or not isinstance(project_name, str) or not project_name.strip():
        raise HTTPException(status_code=400, detail="Nome do projeto inválido ou ausente.")
    if not company_id or not isinstance(company_id, str) or not company_id.strip():
        raise HTTPException(status_code=400, detail="company_id inválido ou ausente.")

    nome_normalizado = normalize_string_general(project_name)
    project = await mongo_service.get_project_by_normalized_name(nome_normalizado, company_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    project_id = getattr(project, "id", None) or getattr(project, "_id", None) or project.get("_id")
    if not project_id:
        raise HTTPException(status_code=500, detail="Projeto encontrado, mas sem ID válido.")
    return project_id
