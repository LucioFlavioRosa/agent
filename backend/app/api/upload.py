import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends, Request
from pydantic import BaseModel

from ..middleware.auth_middleware import get_current_user
from ..services.blob_storage_service import upload_docx_to_blob
from ..services.docx_parser_service import extract_text_from_docx

router = APIRouter()
logger = logging.getLogger("upload_api")

class UploadDocxResponse(BaseModel):
    blob_url: str
    extracted_text: str
    message: str

@router.post("/docx", response_model=UploadDocxResponse, tags=["Upload"])
async def upload_docx(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    projeto: str = Form(...),
    analysis_name: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Recebe o arquivo .docx, valida, extrai o texto e faz upload para o Azure Blob Storage.
    Retorna o texto extraído para que o frontend possa revisá-lo ou enviá-lo para análise.
    """
    usuario_executor = current_user.get("usuario_executor") or current_user.get("sub")

    # 1. Validar extensão
    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Apenas arquivos .docx são permitidos.")

    # 2. Extrair texto do docx (Processamento síncrono para retorno imediato)
    try:
        texto_extraido = await extract_text_from_docx(file)
        # Resetar o ponteiro do arquivo para o upload, pois a leitura anterior pode tê-lo movido
        await file.seek(0)
    except Exception as e:
        logger.error(f"Erro ao extrair texto: {e}")
        raise HTTPException(status_code=400, detail=f"Erro ao processar o arquivo DOCX: {str(e)}")

    # 3. Salvar arquivo no Blob Storage
    # Define a estrutura de pastas: usuario/projeto/arquivos_recebidos/docx/nome_analise.docx
    blob_folder = f"{usuario_executor}/{projeto}/arquivos_recebidos/docx"
    blob_filename = f"{analysis_name}.docx"

    try:
        # Nota: O upload pode ser mantido em background se não precisarmos da URL validada instantaneamente,
        # mas geralmente queremos garantir que salvou antes de retornar 200 OK.
        # Se 'upload_docx_to_blob' for muito demorado, mantenha em background_tasks, mas aqui vou aguardar
        # para garantir a integridade do fluxo.
        blob_url = await upload_docx_to_blob(file, blob_folder, blob_filename, background_tasks)
    except ValueError as ve:
        logger.error(f"Erro de configuração do Blob Storage: {ve}")
        raise HTTPException(status_code=503, detail="Serviço de armazenamento temporariamente indisponível")
    except Exception as e:
        logger.error(f"Erro inesperado no Blob Storage: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo: {str(e)}")

    return UploadDocxResponse(
        blob_url=blob_url,
        extracted_text=texto_extraido,
        message="Arquivo processado com sucesso. Pronto para análise."
    )
