import logging
from backend.app.services.blob_storage_service import BlobStorageService

logger = logging.getLogger("context_retrieval")

class ContextRetrievalService:
    def __init__(self, blob_storage_service: BlobStorageService):
        self.blob_storage_service = blob_storage_service

    async def build_context_string(self, project_id: str, context_used: dict) -> str:
        """
        Itera sobre o dicionário context_used, baixa os .md do Azure 
        e formata tudo em uma única string gigante de contexto.
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

            # Reconstrói o caminho do Blob conforme o padrão que você salvou no banco
            blob_path = f"projects/{project_id}/{category}/{job_id}.md"

            try:
                logger.info(f"[ContextRetrieval] Baixando artefato '{category}' de: {blob_path}")
                
                # ATENÇÃO: Substitua 'read_blob_as_text' pelo método real que você 
                # tem no seu BlobStorageService para ler o conteúdo do arquivo.
                conteudo_md = await self.blob_storage_service.read_blob_as_text(blob_path)

                if conteudo_md:
                    context_parts.append(f"### {category.upper()}:\n{conteudo_md}\n")
                else:
                    logger.warning(f"[ContextRetrieval] O artefato {blob_path} retornou vazio.")

            except Exception as e:
                logger.error(f"[ContextRetrieval] Falha ao baixar o contexto {category} ({blob_path}): {e}")
                # Dependendo do seu nível de rigor, você pode lançar um erro aqui
                # para impedir a IA de alucinar por falta de contexto.

        # Junta tudo com quebras de linha duplas para o Markdown ficar legível
        return "\n\n".join(context_parts)
