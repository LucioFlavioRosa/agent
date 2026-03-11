import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

router = APIRouter()
logger = logging.getLogger("mcp_prototype_reports_api")

@router.get("/{project_id}/{job_id}")
async def get_generated_report(
    request: Request,
    project_id: str,
    job_id: str,
    company_id: str = Query(..., description="ID da empresa para acessar o blob"),
    filename: Optional[str] = Query("index.html", description="Nome do arquivo")
):
    """
    Recupera um protótipo gerado pela IA (HTML) diretamente do Azure Blob Storage.
    """
    logger.info(f"[MCP Reports] Lendo: company={company_id}, project={project_id}, job={job_id}, file={filename}")
    
    blob_service = getattr(request.app.state, "blob_storage_service", None)
    
    if not blob_service:
        raise HTTPException(status_code=500, detail="Serviço de Blob não disponível.")

    blob_path = f"{project_id}/{job_id}/{filename}"
    
    try:
        # Baixa o arquivo do Blob Storage
        file_bytes = await blob_service.download_document(
            company_id=company_id,
            blob_path=blob_path,
            group_id=None 
        )
        
        # O HTML e o Markdown são lidos como texto (utf-8)
        texto_relatorio = file_bytes.decode('utf-8')
        
        return JSONResponse(
            status_code=200,
            content={"report": texto_relatorio}
        )
        
    except Exception as e:
        erro_msg = str(e)
        logger.error(f"[MCP Reports] Erro ao baixar {blob_path}: {erro_msg}")
        
        # 🚀 AGORA ELE RECONHECE O VOCABULÁRIO DA AZURE
        if "não encontrado" in erro_msg.lower() or "not found" in erro_msg.lower() or "does not exist" in erro_msg.lower() or "blobnotfound" in erro_msg.lower():
             raise HTTPException(status_code=404, detail=f"O arquivo {filename} ainda não foi salvo no Azure Blob.")
             
        # 🚀 COLOQUE O erro_msg AQUI PARA APARECER NO FRONTEND!
        raise HTTPException(status_code=500, detail=f"Erro interno do Blob: {erro_msg}")
