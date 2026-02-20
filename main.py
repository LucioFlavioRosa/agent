import logging
import json
from typing import Optional
from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import JSONResponse

# --- CONFIGURAÇÃO DE LOGGING PARA AZURE APP SERVICE ---
# O Azure App Service captura logs emitidos para stdout automaticamente
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_debug_logger")

app = FastAPI(
    title="MCP - Debug de Payload",
    description="Serviço temporário para imprimir os payloads recebidos do backend.",
    version="1.0.0"
)

# Adicionamos as duas rotas para garantir que vai capturar indepentente da URL base configurada
@app.post("/api/v1/analysis/start", tags=["Debug"])
@app.post("/start", tags=["Debug"])
async def start_analysis_debug(
    request: Request,
    project_id: str = Form(...),
    job_id: str = Form(...),
    company_id: str = Form(...),
    group_ids: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    nome_projeto: Optional[str] = Form(None),
    analysis_type: Optional[str] = Form(None),
    branch: Optional[str] = Form(None),
    repository: Optional[str] = Form(None),
    comentario_extra: Optional[str] = Form(None),
    arquivo_docx: Optional[UploadFile] = File(None)
):
    logger.info("========== NOVO INÍCIO DE ANÁLISE RECEBIDO ==========")
    
    # 1. Log dos campos obrigatórios e strings simples
    logger.info(f"JOB_ID: {job_id}")
    logger.info(f"PROJECT_ID: {project_id}")
    logger.info(f"COMPANY_ID: {company_id}")
    logger.info(f"EMAIL: {email}")
    logger.info(f"NOME_PROJETO: {nome_projeto}")
    logger.info(f"ANALYSIS_TYPE: {analysis_type}")
    logger.info(f"BRANCH: {branch}")
    logger.info(f"REPOSITORY: {repository}")
    logger.info(f"COMENTARIO_EXTRA: {comentario_extra}")
    
    # 2. Inspecionando o group_ids detalhadamente
    logger.info(f"GROUP_IDS (RAW): '{group_ids}' | Tipo recebido: {type(group_ids)}")
    if group_ids:
        try:
            # Tenta decodificar o JSON string para ver se o backend mandou certinho
            parsed_groups = json.loads(group_ids)
            logger.info(f"GROUP_IDS (PARSED): {parsed_groups} | Tipo convertido: {type(parsed_groups)}")
        except json.JSONDecodeError as e:
            logger.warning(f"GROUP_IDS não é um JSON válido. Erro de parse: {e}")
    else:
        logger.info("GROUP_IDS: Nenhum grupo recebido (vazio ou None).")

    # 3. Verificando o arquivo (se foi enviado)
    if arquivo_docx:
        logger.info(f"ARQUIVO: Recebido! Nome: '{arquivo_docx.filename}' | Content-Type: '{arquivo_docx.content_type}'")
        try:
            # Lê apenas os primeiros 50 bytes para provar que o conteúdo chegou sem travar a memória
            conteudo_teste = await arquivo_docx.read(50)
            logger.info(f"ARQUIVO (Primeiros bytes): {conteudo_teste}")
        except Exception as e:
            logger.error(f"ARQUIVO: Erro ao tentar ler os bytes: {e}")
    else:
        logger.info("ARQUIVO: Nenhum arquivo .docx foi anexado na requisição.")

    logger.info("=====================================================")

    # Retorna 202 para o backend saber que a requisição bateu aqui com sucesso
    return JSONResponse(
        status_code=202,
        content={
            "message": "Payload recebido pelo MCP. Verifique os logs do App Service.",
            "job_id": job_id,
            "status": "debug_success"
        }
    )

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "message": "MCP Debugger is running"}

if __name__ == "__main__":
    import uvicorn
    # Inicia o servidor localmente na porta 8080 (o Azure costuma usar a variável PORT ou default 8000/8080)
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
