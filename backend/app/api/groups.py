from fastapi import APIRouter, HTTPException, Query, Path, Depends
from backend.app.services.mongodb_service import MongoDBService
from backend.app.utils.logging_utils import log_request_received, log_response_sent
import logging
from typing import List, Optional

router = APIRouter()
logger = logging.getLogger("groups_api")

async def get_mongo_service(request):
    return request.app.state.mongo_service

@router.get("/groups/{group_id}", tags=["Groups"])
async def get_group_by_id(
    group_id: str = Path(..., description="ID do grupo a ser consultado"),
    mongo_service: MongoDBService = Depends(get_mongo_service)
):
    log_request_received(endpoint=f"/groups/{group_id}", payload={"group_id": group_id})
    logger.info(f"[Groups] Requisição recebida para /groups/{{group_id}}: group_id={group_id}")
    try:
        group = await mongo_service.get_group_by_id(group_id)
        if not group:
            logger.warning(f"[Groups] Grupo não encontrado: group_id={group_id}")
            raise HTTPException(status_code=404, detail="Grupo não encontrado.")
        response = group.dict() if hasattr(group, 'dict') else group
        log_response_sent(endpoint=f"/groups/{group_id}", response=response)
        return response
    except HTTPException as exc:
        log_response_sent(endpoint=f"/groups/{group_id}", response={"detail": exc.detail})
        raise
    except Exception as e:
        logger.error(f"[Groups] Erro ao buscar grupo: {e}")
        log_response_sent(endpoint=f"/groups/{group_id}", response={"detail": str(e)})
        raise HTTPException(status_code=500, detail="Erro interno ao buscar grupo.")

@router.get("/groups", tags=["Groups"])
async def list_groups_by_company(
    company_id: str = Query(..., description="ID da empresa para filtrar grupos"),
    mongo_service: MongoDBService = Depends(get_mongo_service)
):
    log_request_received(endpoint="/groups", payload={"company_id": company_id})
    logger.info(f"[Groups] Requisição recebida para /groups: company_id={company_id}")
    if not company_id or not isinstance(company_id, str) or not company_id.strip():
        logger.warning(f"[Groups] company_id inválido ou ausente: {company_id}")
        log_response_sent(endpoint="/groups", response={"detail": "company_id é obrigatório."})
        raise HTTPException(status_code=400, detail="company_id é obrigatório.")
    try:
        groups = await mongo_service.list_groups_by_company(company_id)
        response = [g.dict() if hasattr(g, 'dict') else g for g in groups]
        log_response_sent(endpoint="/groups", response=response)
        return response
    except Exception as e:
        logger.error(f"[Groups] Erro ao listar grupos: {e}")
        log_response_sent(endpoint="/groups", response={"detail": str(e)})
        raise HTTPException(status_code=500, detail="Erro interno ao listar grupos.")
