import logging
from typing import Optional
from backend.app.services.blob_storage_service import BlobStorageService
from backend.app.config.agent_mapping import AGENT_CONFIG # 🚀 IMPORTAMOS O MAPA

logger = logging.getLogger("context_retrieval")

class ContextRetrievalService:
    def __init__(self, blob_storage_service: BlobStorageService):
        self.blob_storage_service = blob_storage_service

    async def build_context_string(self, company_id: str, project_id: str, context_used: dict, group_ids: Optional[str] = None) -> str:
        logger.info(f"[ContextRetrievalService] build_context_string chamado: company_id='{company_id}', project_id='{project_id}', context_used='{context_used}', group_ids='{group_ids}'")
        if not context_used:
            logger.info("[ContextRetrievalService] Nenhum contexto usado fornecido. Retornando string vazia.")
            return ""

        context_parts = ["O contexto atual do projeto é composto pelos seguintes artefatos:\n"]

        for key, job_id in context_used.items():
            logger.info(f"[ContextRetrievalService] Processando item de contexto: key='{key}', job_id='{job_id}'")
            if not job_id:
                logger.info(f"[ContextRetrievalService] job_id vazio para key='{key}', ignorando.")
                continue

            # Extrai o nome da categoria. Ex: "epics_job_id" vira "epics"
            category = key.replace("_job_id", "")
            logger.info(f"[ContextRetrievalService] Categoria identificada: '{category}'")
            
            # 🚀 Reconstrói o nome do agente (ou você pode mapear isso de forma mais direta depois)
            # Para descobrir o nome do arquivo, precisamos achar o agente daquela categoria
            nome_arquivo_esperado = f"{category}.md" # Fallback
            for agent_key, config in AGENT_CONFIG.items():
                if category in agent_key: 
                    nome_arquivo_esperado = config["output_filename"]
                    logger.info(f"[ContextRetrievalService] Nome de arquivo esperado identificado via AGENT_CONFIG: '{nome_arquivo_esperado}'")
                    break

            # Reconstrói o caminho do Blob com o nome oficial configurado no mapeamento
            blob_path_interno = f"{project_id}/{job_id}/{nome_arquivo_esperado}" 
            logger.info(f"[ContextRetrievalService] Caminho do blob para download: '{blob_path_interno}'")

            try:
                logger.info(f"[ContextRetrievalService] Baixando contexto de '{blob_path_interno}'")
                file_bytes = await self.blob_storage_service.download_document(
                    company_id=company_id,
                    blob_path=blob_path_interno,
                    group_id=group_ids
                )
                conteudo_md = file_bytes.decode('utf-8')
                if conteudo_md:
                    logger.info(f"[ContextRetrievalService] Contexto adicionado com sucesso para categoria '{category}'.")
                    context_parts.append(f"### {category.upper()}:\n{conteudo_md}\n")
                else:
                    logger.info(f"[ContextRetrievalService] Conteúdo vazio para categoria '{category}'.")
                    
            except Exception as e:
                logger.error(f"⚠️ [ContextRetrievalService] Falha ao baixar '{blob_path_interno}': {e}", exc_info=True)
                context_parts.append(f"### {category.upper()}:\n(Contexto indisponível)\n")

        logger.info("[ContextRetrievalService] Context string montada com sucesso.")
        return "\n\n".join(context_parts)
