import json
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks

# Importa apenas as ferramentas de documento e o serviço principal
from app.utils.document_parser import extract_text_from_docx
from app.services.prototype_service import process_analysis_task

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("mcp_prototype.main")

app = FastAPI(title="MCP - Prototype Generator", version="1.0")

# ❌ Removemos app.add_event_handler("startup", connect_to_mongo)
# ❌ Removemos app.add_event_handler("shutdown", close_mongo_connection)

@app.post("/analyze")
async def analyze_endpoint(
    background_tasks: BackgroundTasks,
    payload: str = Form(...),
    arquivo_docx: Optional[UploadFile] = File(None),
    arquivo_identidade: Optional[UploadFile] = File(None)
):
    logger.info("📥 [API] Nova solicitação recebida.")
    
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Payload inválido.")

    texto_instrucoes = await extract_text_from_docx(arquivo_docx)
    texto_identidade = await extract_text_from_docx(arquivo_identidade)

    # Inicia o processamento
    background_tasks.add_task(
        process_analysis_task, 
        payload=data, 
        texto_instrucoes=texto_instrucoes, 
        texto_identidade=texto_identidade
    )

    return {"message": "Processamento iniciado no Blob Storage.", "job_id": data.get("job_id")}
