import logging
from typing import Optional
from backend.app.services.blob_storage_service import BlobStorageService

logger = logging.getLogger("context_retrieval")

class ContextRetrievalService:
    def __init__(self, blob_storage_service: BlobStorageService):
        self.blob_storage_service = blob_storage_service

    async def build_context_string(self, company_id: str, project_id: str, context_used: dict, group_ids: Optional[str] = None) -> str:
        """
        Itera sobre o dicionário context_used, baixa os arquivos .md do Azure Blob Storage
        usando o BlobStorageService existente, e formata tudo em uma única string gigante de contexto.
        """
        if not context_used:
            return ""

        context_parts = []
        context_parts.append("O contexto atual do projeto é composto pelos seguintes artefatos:\n")

        # Exemplo de context_used: {"epics_job_id": "job-123", "features_job_id": "job-456"}
        for key, job_id in context_used.items():
            if not job_id:
                continue

            # Extrai o nome da categoria. Ex: "epics_job_id" vira "epics"
            category = key.replace("_job_id", "")

            # Reconstrói o caminho do Blob no padrão que o Azure (e o seu método de save) espera
            # Formato do save_document: f"{project_id}/{job_id}/{filename}"
            # Assumimos que o filename salvo foi '{job_id}.md' ou algo similar.
            # Se você salvou com um nome fixo como 'report.md', ajuste a linha abaixo!
            blob_path_interno = f"{project_id}/{job_id}/{job_id}.md" 

            try:
                logger.info(f"[ContextRetrieval] Baixando contexto '{category}' do job '{job_id}'")
                
                # 🚀 Chama o SEU método existente
                file_bytes = await self.blob_storage_service.download_document(
                    company_id=company_id,
                    blob_path=blob_path_interno,
                    group_id=group_ids
                )

                # Decodifica de bytes para string (texto em Markdown)
                conteudo_md = file_bytes.decode('utf-8')

                if conteudo_md:
                    context_parts.append(f"### {category.upper()}:\n{conteudo_md}\n")
                else:
                    logger.warning(f"[ContextRetrieval] O arquivo '{blob_path_interno}' retornou vazio.")

            except Exception as e:
                logger.error(f"⚠️ [ContextRetrieval] Falha ao baixar contexto de '{category}' ({blob_path_interno}): {e}")
                # Como é contexto histórico, apenas logamos o erro e pulamos.
                # Se for crítico para a sua IA, você pode dar um raise aqui.
                context_parts.append(f"### {category.upper()}:\n(Contexto indisponível no momento devido a erro de leitura)\n")

        # Junta tudo com quebras de linha duplas
        return "\n\n".join(context_parts)
