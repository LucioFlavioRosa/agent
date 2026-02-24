import logging
from typing import Optional
from backend.app.services.blob_storage_service import BlobStorageService
from backend.app.config.agent_mapping import AGENT_CONFIG # 🚀 IMPORTAMOS O MAPA

logger = logging.getLogger("context_retrieval")

class ContextRetrievalService:
    def __init__(self, blob_storage_service: BlobStorageService):
        self.blob_storage_service = blob_storage_service

    async def build_context_string(self, company_id: str, project_id: str, context_used: dict, group_ids: Optional[str] = None) -> str:
        if not context_used:
            return ""

        context_parts = ["O contexto atual do projeto é composto pelos seguintes artefatos:\n"]

        for key, job_id in context_used.items():
            if not job_id:
                continue

            # Extrai o nome da categoria. Ex: "epics_job_id" vira "epics"
            category = key.replace("_job_id", "")
            
            # 🚀 Reconstrói o nome do agente (ou você pode mapear isso de forma mais direta depois)
            # Para descobrir o nome do arquivo, precisamos achar o agente daquela categoria
            nome_arquivo_esperado = f"{category}.md" # Fallback
            for agent_key, config in AGENT_CONFIG.items():
                if category in agent_key: 
                    nome_arquivo_esperado = config["output_filename"]
                    break

            # Reconstrói o caminho do Blob com o nome oficial configurado no mapeamento
            blob_path_interno = f"{project_id}/{job_id}/{nome_arquivo_esperado}" 

            try:
                logger.info(f"[ContextRetrieval] Baixando contexto de {blob_path_interno}")
                file_bytes = await self.blob_storage_service.download_document(
                    company_id=company_id,
                    blob_path=blob_path_interno,
                    group_id=group_ids
                )
                conteudo_md = file_bytes.decode('utf-8')
                if conteudo_md:
                    context_parts.append(f"### {category.upper()}:\n{conteudo_md}\n")
                    
            except Exception as e:
                logger.error(f"⚠️ [ContextRetrieval] Falha ao baixar {blob_path_interno}: {e}")
                context_parts.append(f"### {category.upper()}:\n(Contexto indisponível)\n")

        return "\n\n".join(context_parts)
