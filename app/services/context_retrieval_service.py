import logging
from typing import Optional
from app.services.blob_storage_service import BlobStorageService
from app.config.agent_mapping import AGENT_CONFIG

logger = logging.getLogger("mcp_prototype.context_retrieval")

class ContextRetrievalService:
    # 🚀 CORREÇÃO 2: Recebe o serviço via Injeção de Dependência
    def __init__(self, blob_storage_service: BlobStorageService):
        self.blob_storage_service = blob_storage_service

    async def build_context_string(self, company_id: str, project_id: str, context_used: dict, group_ids: Optional[str] = None) -> str:
        """
        Lê os arquivos salvos no Blob Storage com base nos Job IDs fornecidos no contexto.
        """
        logger.info(f"context_build_iniciado | company_id={company_id} | project_id={project_id} | context_keys={list(context_used.keys())}")
        
        if not context_used:
            return ""

        context_parts = ["O contexto atual do projeto para referência é:\n"]
        itens_adicionados = 0

        for key, job_id in context_used.items():
            if not job_id:
                continue
            
            # Converte 'prototype_job_id' em 'prototype'
            category = key.replace("_job_id", "")
            
            # 🚀 LÓGICA DE NOME DE ARQUIVO:
            # Tenta encontrar o nome do arquivo de saída no AGENT_CONFIG (ex: 'index.html')
            nome_arquivo_esperado = f"{category}.md" # Fallback padrão
            
            for agent_key, config in AGENT_CONFIG.items():
                # Se a categoria (ex: 'prototype') estiver no nome do agente, usa o output_filename dele
                if category in agent_key:
                    nome_arquivo_esperado = config.get("output_filename", nome_arquivo_esperado)
                    break
            
            blob_path_interno = f"{project_id}/{job_id}/{nome_arquivo_esperado}"
            
            try:
                print(f"🔍 [CONTEXTO] Tentando baixar: {blob_path_interno}", flush=True)
                
                file_bytes = await self.blob_storage_service.download_document(
                    company_id=company_id,
                    blob_path=blob_path_interno,
                    group_id=group_ids
                )
                
                if file_bytes:
                    conteudo = file_bytes.decode('utf-8')
                    # Adiciona ao prompt final
                    context_parts.append(f"--- ARTEFATO ANTERIOR ({category.upper()}) ---\n{conteudo}\n")
                    logger.info(f"context_item_adicionado | categoria={category} | job_id={job_id}")
                    itens_adicionados += 1
                
            except Exception as e:
                # Se um arquivo falhar, apenas avisamos e continuamos para não travar a análise toda
                print(f"⚠️ [CONTEXTO] Falha ao ler {category}: {e}", flush=True)
                logger.warning(f"context_item_falha | categoria={category} | erro={e}")

        if itens_adicionados == 0:
            return ""

        logger.info(f"context_build_finalizado | itens={itens_adicionados}")
        return "\n\n".join(context_parts)
