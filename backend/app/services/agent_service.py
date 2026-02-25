import logging
from pathlib import Path
from typing import Optional
import re

from backend.app.services.context_retrieval_service import ContextRetrievalService
from backend.app.services.blob_storage_service import BlobStorageService # 🚀 IMPORT NOVO
from backend.app.config.agent_mapping import AGENT_CONFIG

logger = logging.getLogger("mcp_agent")

class AgentService:
    def __init__(
        self, 
        context_retrieval_service: ContextRetrievalService, 
        blob_storage_service: BlobStorageService, # 🚀 INJETADO AQUI
        llm_services: dict, 
        *args, **kwargs
    ):
        """
        Inicializa o serviço do agente.
        Recebe os serviços de contexto, de blob storage (para salvar o resultado) e o registro de LLMs.
        """
        self.context_retrieval = context_retrieval_service
        self.blob_storage = blob_storage_service # 🚀 SALVANDO A REFERÊNCIA
        self.llm_services = llm_services

    def _obter_prompt_base(self, analysis_type: Optional[str]) -> str:
        prompt_padrao = "Você é um assistente de IA corporativo. Faça uma análise do documento fornecido."
        logger.info(f"[AgentService] _obter_prompt_base chamado com analysis_type='{analysis_type}'")
        
        if not analysis_type or analysis_type not in AGENT_CONFIG:
            logger.warning(f"⚠️ [AgentService] Agente '{analysis_type}' não mapeado. Usando fallback.")
            logger.info("[AgentService] Retornando prompt padrão por fallback.")
            return prompt_padrao

        nome_arquivo_prompt = AGENT_CONFIG[analysis_type]["prompt_file"]
        logger.info(f"[AgentService] Carregando arquivo de prompt base: {nome_arquivo_prompt}")
        
        diretorio_base = Path(__file__).resolve().parent.parent
        caminho_arquivo = diretorio_base / "prompts" / nome_arquivo_prompt
        
        try:
            if caminho_arquivo.exists() and caminho_arquivo.is_file():
                logger.info(f"[AgentService] Prompt base encontrado: {caminho_arquivo.name}")
                return caminho_arquivo.read_text(encoding="utf-8")
            else:
                logger.warning(f"⚠️ [AgentService] Prompt '{caminho_arquivo.name}' não encontrado fisicamente.")
                logger.info("[AgentService] Retornando prompt padrão por arquivo não encontrado.")
                return prompt_padrao
                
        except Exception as e:
            logger.error(f"❌ [AgentService] Erro ao ler prompt base '{caminho_arquivo}': {e}")
            logger.info("[AgentService] Retornando prompt padrão por exceção.")
            return prompt_padrao

    async def _montar_prompt(
        self, 
        texto_documento: str, 
        analysis_type: Optional[str], 
        comentario_extra: Optional[str],
        company_id: str,
        project_id: str,
        context_used: dict,
        group_ids: Optional[str] = None
    ) -> str:
        """Monta o Mega-Prompt final juntando todas as camadas."""
        logger.info(f"[AgentService] _montar_prompt chamado para job com company_id='{company_id}', project_id='{project_id}', analysis_type='{analysis_type}'")
        prompt = self._obter_prompt_base(analysis_type)
        logger.info("[AgentService] Prompt base carregado com sucesso.")
        prompt += "\n\n"
        
        logger.info("[AgentService] Buscando contexto histórico para montagem do prompt.")
        contexto_historico = await self.context_retrieval.build_context_string(
            company_id=company_id, 
            project_id=project_id, 
            context_used=context_used,
            group_ids=group_ids
        )
        
        if contexto_historico:
            logger.info("[AgentService] Contexto histórico encontrado e adicionado ao prompt.")
            prompt += f"--- CONTEXTO HISTÓRICO (Relatórios Anteriores) ---\n{contexto_historico}\n\n"
        else:
            logger.info("[AgentService] Nenhum contexto histórico encontrado para este job.")
        
        if comentario_extra:
            logger.info("[AgentService] Instruções extras do usuário detectadas e adicionadas ao prompt.")
            prompt += f"--- INSTRUÇÕES ADICIONAIS DO USUÁRIO ---\n{comentario_extra}\n\n"
            
        if texto_documento:
            logger.info("[AgentService] Documento atual para análise detectado e adicionado ao prompt.")
            prompt += f"--- DOCUMENTO ATUAL PARA ANÁLISE ---\n{texto_documento}\n\n"
        else:
            logger.info("[AgentService] Nenhum documento atual fornecido para análise.")
        
        prompt += "Gere o relatório final estruturado em formato Markdown."
        logger.info("[AgentService] Prompt final montado com sucesso.")
        return prompt

    async def executar_analise(self, task_payload: dict, texto_extraido: str) -> str:
        """
        Orquestra a chamada do LLM consultando o AGENT_CONFIG e SALVA o resultado.
        """
        job_id = task_payload.get('job_id')
        analysis_type = task_payload.get("analysis_type")
        company_id = task_payload.get("company_id")
        project_id = task_payload.get("project_id")
        group_ids = task_payload.get("group_ids")
        
        logger.info(f"[AgentService] executar_analise iniciado: job_id='{job_id}', analysis_type='{analysis_type}', company_id='{company_id}', project_id='{project_id}'")
        
        try:
            # 1. Monta o super prompt
            logger.info("[AgentService] Montando mega-prompt para análise.")
            mega_prompt = await self._montar_prompt(
                texto_documento=texto_extraido,
                analysis_type=analysis_type,
                comentario_extra=task_payload.get("comentario_extra"),
                company_id=company_id,
                project_id=project_id,
                context_used=task_payload.get("context_used", {}), 
                group_ids=group_ids
            )
            logger.info("[AgentService] Mega-prompt montado com sucesso.")
            
            # 2. ROTEAMENTO DINÂMICO
            logger.info("[AgentService] Identificando serviço LLM e modelo.")
            config_agente = AGENT_CONFIG.get(analysis_type)
            if not config_agente:
                logger.error(f"Tipo de análise '{analysis_type}' não encontrado no AGENT_CONFIG.")
                raise ValueError(f"Tipo de análise '{analysis_type}' não encontrado no AGENT_CONFIG.")

            nome_servico = config_agente.get("service")
            nome_modelo = config_agente.get("llm_model")
            nome_arquivo_saida = config_agente.get("output_filename") # 🚀 Pega o nome do arquivo final!

            logger.info(f"[AgentService] Serviço LLM identificado: '{nome_servico}', Modelo: '{nome_modelo}', Output: '{nome_arquivo_saida}'")

            llm_service = self.llm_services.get(nome_servico)
            if not llm_service:
                logger.error(f"Serviço LLM '{nome_servico}' não foi registrado no llm_services.")
                raise ValueError(f"Serviço LLM '{nome_servico}' não foi registrado no llm_services.")

            logger.info(f"🧠 [AgentService] Delegando job {job_id} para o serviço '{nome_servico}' com modelo '{nome_modelo}'")

            # 3. Executa a IA
            logger.info("[AgentService] Chamando LLM para gerar resposta.")
            resposta_llm = await llm_service.gerar_texto(
                prompt=mega_prompt, 
                modelo=nome_modelo,
                company_id=company_id, 
                group_id=group_ids
            )
            logger.info(f"[AgentService] Resposta da LLM recebida para job_id='{job_id}'.")
            
            # 4. 🚀 SALVA O RESULTADO NO BLOB STORAGE
            if resposta_llm and nome_arquivo_saida:
                logger.info(f"💾 [AgentService] Convertendo resposta para bytes e salvando como '{nome_arquivo_saida}'...")
                
                # Converte a string Markdown para bytes (exigência do seu BlobStorageService)
                file_bytes = resposta_llm.encode('utf-8')
                
                # Salva no Azure Blob Storage
                logger.info(f"[AgentService] Salvando relatório final no Blob Storage: company_id='{company_id}', project_id='{project_id}', job_id='{job_id}', filename='{nome_arquivo_saida}', group_id='{group_ids}'")
                caminho_blob = await self.blob_storage.save_document(
                    company_id=company_id,
                    project_id=project_id,
                    job_id=job_id,
                    file_data=file_bytes,
                    filename=nome_arquivo_saida,
                    group_id=group_ids
                )
                logger.info(f"✅ [AgentService] Relatório final salvo com sucesso em: {caminho_blob}")

            logger.info(f"[AgentService] Job '{job_id}' finalizado com sucesso.")
            return resposta_llm
        except Exception as e:
            logger.error(f"❌ [AgentService] Erro crítico ao executar análise para job_id='{job_id}': {e}", exc_info=True)
            raise
