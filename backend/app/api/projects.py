import logging
from fastapi import APIRouter, HTTPException, Query
import httpx
from backend.app.core.config import settings

router = APIRouter()
logger = logging.getLogger("projects_api")

@router.get("/check", tags=["Projects"])
async def check_project(
    nome_projeto: str = Query(..., description="Nome do projeto a ser verificado"),
    email: str = Query(..., description="Email do usuário"),
    empresa: str = Query(..., description="Empresa do usuário")
):
    mcp_url = settings.MCP_SERVER_BASE_URL.rstrip("/") + "/projects/check"
    params = {
        "nome_projeto": nome_projeto,
        "email": email,
        "empresa": empresa
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(mcp_url, params=params)
            if response.status_code != 200:
                logger.error(f"Erro MCP /projects/check: {response.status_code} {response.text}")
                raise HTTPException(status_code=502, detail="Erro ao consultar MCP.")
            return response.json()
    except Exception as e:
        logger.error(f"Falha ao consultar MCP /projects/check: {e}")
        raise HTTPException(status_code=502, detail="Erro ao consultar MCP.")

@router.get("/list", tags=["Projects"])
async def list_projects(
    email: str = Query(..., description="Email do usuário"),
    empresa: str = Query(..., description="Empresa do usuário")
):
    mcp_url = settings.MCP_SERVER_BASE_URL.rstrip("/") + "/projects/list"
    params = {
        "email": email,
        "empresa": empresa
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(mcp_url, params=params)
            if response.status_code != 200:
                logger.error(f"Erro MCP /projects/list: {response.status_code} {response.text}")
                raise HTTPException(status_code=502, detail="Erro ao consultar MCP.")
            return response.json()
    except Exception as e:
        logger.error(f"Falha ao consultar MCP /projects/list: {e}")
        raise HTTPException(status_code=502, detail="Erro ao consultar MCP.")
