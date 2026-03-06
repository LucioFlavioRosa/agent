
import logging
from typing import Optional
from backend.app.services.blob_storage_service import BlobStorageService
from backend.app.config.agent_mapping import AGENT_CONFIG

logger = logging.getLogger("mcp_doc_structured")

class ContextRetrievalService:
    def __init__(self, blob_storage_service: BlobStorageService):
        self.blob_storage_service = blob_storage_service

    async def build_context_string(self, company_id: str, project_id: str, context_used: dict, group_ids: Optional[str] = None) -> str:
        logger.info(f"context_build_iniciado | company_id={company_id} | project_id={project_id} | group_ids={group_ids} | context_keys={list(context_used.keys())}")
        if not context_used:
            logger.info("context_build_finalizado | itens=0")
            return ""

        context_parts = ["O contexto atual do projeto é composto pelos seguintes artefatos:\n"]
        itens_adicionados = 0

        for key, job_id in context_used.items():
            if not job_id:
                continue
            category = key.replace("_job_id", "")
            nome_arquivo_esperado = f"{category}.md"
            for agent_key, config in AGENT_CONFIG.items():
                if category in agent_key:
                    nome_arquivo_esperado = config["output_filename"]
                    break
            blob_path_interno = f"{project_id}/{job_id}/{nome_arquivo_esperado}"
            try:
                file_bytes = await self.blob_storage_service.download_document(
                    company_id=company_id,
                    blob_path=blob_path_interno,
                    group_id=group_ids
                )
                conteudo_md = file_bytes.decode('utf-8')
                if conteudo_md:
                    context_parts.append(f"### {category.upper()}:\n{conteudo_md}\n")
                else:
                    context_parts.append(f"### {category.upper()}:\n(Contexto indisponível)\n")
                logger.info(f"context_item_adicionado | categoria={category} | job_id={job_id}")
                itens_adicionados += 1
            except Exception as e:
                context_parts.append(f"### {category.upper()}:\n(Contexto indisponível)\n")
                logger.info(f"context_item_adicionado | categoria={category} | job_id={job_id} | erro=sim")
                itens_adicionados += 1

        logger.info(f"context_build_finalizado | itens={itens_adicionados}")
        return "\n\n".join(context_parts)
