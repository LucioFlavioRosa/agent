from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import JSONResponse
from backend.app.services.redis_session_service import RedisSessionService
import logging
import httpx
from backend.app.core.config import settings

router = APIRouter()
logger = logging.getLogger("session_api")

@router.get("/project/{project_id}/{job_id}/reports")
async def get_project_reports(
    project_id: str,
    job_id: str,
    email: str = Query(..., description="Email do usuário"),
    empresa: str = Query(..., description="Empresa do usuário")
):
    mcp_url = settings.MCP_SERVER_BASE_URL.rstrip("/") + f"/session/project/{project_id}/{job_id}/reports"
    params = {
        "email": email,
        "empresa": empresa
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(mcp_url, params=params)
            logger.info(f"MCP response [{response.status_code}]: {response.text}")
            if response.status_code == 202:
                return JSONResponse(
                    content=response.json(),
                    status_code=status.HTTP_202_ACCEPTED
                )
            elif response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Erro MCP /session/project/{project_id}/{job_id}/reports: {response.status_code} {response.text}")
                raise HTTPException(status_code=502, detail="Erro ao consultar MCP.")
    except Exception as e:
        logger.error(f"Falha ao consultar MCP /session/project/{project_id}/{job_id}/reports: {e}")
        raise HTTPException(status_code=502, detail="Erro ao consultar MCP.")
