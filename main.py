import logging
import uuid
import os
from fastapi import FastAPI, APIRouter
from pydantic import BaseModel
from typing import Optional

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MockMCP")

app = FastAPI(title="MCP Mock Service", version="1.0.0")

# Router para agrupar as rotas
router = APIRouter()

# Modelo de Dados (Payload que o Backend envia)
class FakeMCPStartPayload(BaseModel):
    projeto: str
    analysis_type: str
    arquivo_docx: Optional[str] = None
    comentario_usuario: Optional[str] = None
    usuario_executor: Optional[str] = None
    session_id: Optional[str] = None

@router.get("/")
def home():
    return {"status": "Mock Service Online"}

@router.post("/start")
async def start_analysis_mock(payload: FakeMCPStartPayload):
    """
    Simula o endpoint de início de análise.
    """
    job_id = f"job-external-mock-{uuid.uuid4().hex[:8]}"
    
    logger.info(f"⚡ [MOCK EXTERNO] Recebi chamada do Backend!")
    logger.info(f"📂 Projeto: {payload.projeto}")
    logger.info(f"👤 Executor: {payload.usuario_executor}")
    
    if payload.arquivo_docx:
        # Simula leitura do texto ou URL
        preview = payload.arquivo_docx[:50] + "..." if len(payload.arquivo_docx) > 50 else payload.arquivo_docx
        logger.info(f"📄 DOCX: {preview}")

    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Job aceito pelo Mock Standalone (Serviço Separado)"
    }

# Registra a rota com o prefixo correto
# A URL final será: SEU_DOMINIO/fake-mcp/api/v1/analysis/start
app.include_router(router, prefix="/fake-mcp/api/v1/analysis")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
