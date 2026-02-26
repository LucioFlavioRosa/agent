import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

# Usaremos o serviço de Blob que já existe no escopo do Request (Injeção via app.state)
router = APIRouter()
logger = logging.getLogger("mcp_reports_api")

@router.get("/{project_id}/{job_id}")
async def get_generated_report(
    request: Request,
    project_id: str,
    job_id: str,
    company_id: str = Query(..., description="ID da empresa para acessar o container do blob"),
    filename: Optional[str] = Query("epics.md", description="Nome do arquivo gerado (ex: epics.md, features.md)")
):
    """
    Recupera um relatório gerado pela IA diretamente do Azure Blob Storage.
    """
    logger.info(f"[MCP Reports] Requisição para ler relatório: company_id={company_id}, project_id={project_id}, job_id={job_id}, arquivo={filename}")
    
    # 1. Puxa a instância do serviço de Blob que foi criada no main.py
    blob_service = getattr(request.app.state, "blob_storage_service", None)
    
    if not blob_service:
        logger.error("[MCP Reports] Serviço de Blob Storage não inicializado no app.state.")
        raise HTTPException(status_code=500, detail="Serviço de armazenamento interno não disponível.")

    # 2. Monta o caminho exato de onde o Worker salva o arquivo de saída
    # O caminho oficial do Worker (queue_service.py) é: {company_id}/{project_id}/{job_id}/{nome_arquivo_saida}
    blob_path = f"{project_id}/{job_id}/{filename}"
    
    try:
        # 3. Baixa o arquivo do Blob Storage
        file_bytes = await blob_service.download_document(
            company_id=company_id,
            blob_path=blob_path,
            group_id=None # Ajuste se o seu sistema precisar de group_id para ler segredos
        )
        
        # 4. Converte os bytes do Markdown para Texto String
        texto_relatorio = file_bytes.decode('utf-8')
        
        logger.info(f"[MCP Reports] Sucesso ao ler o arquivo {filename}. Tamanho: {len(texto_relatorio)} caracteres.")
        
        # 5. Retorna exatamente o que o mcp_client_service do Backend espera
        return JSONResponse(
            status_code=200,
            content={"report": texto_relatorio}
        )
        
    except Exception as e:
        erro_msg = str(e)
        logger.error(f"[MCP Reports] Erro ao baixar o blob {blob_path}: {erro_msg}")
        
        if "não encontrado" in erro_msg.lower() or "not found" in erro_msg.lower():
             raise HTTPException(status_code=404, detail="Arquivo de relatório não encontrado no armazenamento.")
             
        raise HTTPException(status_code=500, detail="Erro interno ao acessar o armazenamento.")
