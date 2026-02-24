import logging
from pathlib import Path
from typing import Optional
import re

from backend.app.services.context_retrieval_service import ContextRetrievalService
from backend.app.config.agent_mapping import AGENT_CONFIG

logger = logging.getLogger("mcp_agent")

class AgentService:
    def __init__(self, context_retrieval_service: ContextRetrievalService, llm_services: dict, *args, **kwargs):
        """
        Inicializa o serviço do agente.
        Recebe o ContextRetrievalService injetado para buscar relatórios antigos no Blob Storage.
        Recebe llm_services, um dicionário mapeando nomes de serviços para suas instâncias.
        Ex: {"claude_aws_service": instancia_claude, "azure_openai_service": instancia_azure}
        """
        self.context_retrieval = context_retrieval_service
        self.llm_services = llm_services

    def _obter_prompt_base(self, analysis_type: Optional[str]) -> str:
        """
        Lê o arquivo Markdown correspondente ao tipo de análise na pasta 'prompts'.
        Este arquivo dita as regras de negócio e o comportamento geral da IA.
        """
        prompt_padrao = "Você é um assistente de IA corporativo. Faça uma análise do documento fornecido."
        
        if not analysis_type or analysis_type not in AGENT_CONFIG:
            logger.warning(f"⚠️ [AgentService] Agente '{analysis_type}' não mapeado. Usando fallback.")
            return prompt_padrao

        # 🚀 Puxa o nome do arquivo do nosso mapeamento
        nome_arquivo_prompt = AGENT_CONFIG[analysis_type]["prompt_file"]
        
        diretorio_base = Path(__file__).resolve().parent.parent
        caminho_arquivo = diretorio_base / "prompts" / nome_arquivo_prompt
        
        try:
            if caminho_arquivo.exists() and caminho_arquivo.is_file():
                logger.info(f"[AgentService] Carregando prompt base: {caminho_arquivo.name}")
                return caminho_arquivo.read_text(encoding="utf-8")
            else:
                logger.warning(f"⚠️ [AgentService] Prompt '{caminho_arquivo.name}' não encontrado fisicamente.")
                return prompt_padrao
                
        except Exception as e:
            logger.error(f"❌ [AgentService] Erro ao ler prompt base '{caminho_arquivo}': {e}")
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
        """
        Monta o Mega-Prompt final juntando todas as camadas (Base + Histórico + Extras + Documento atual).
        Como busca dados no Blob Storage, esta função agora é ASSÍNCRONA.
        """
        # 1. Carrega as regras de comportamento (.md local)
        prompt = self._obter_prompt_base(analysis_type)
        prompt += "\n\n"
        
        # 2. Carrega o histórico (relatórios anteriores) do Blob Storage
        # Chama o serviço especialista que criamos para montar a string gigante
        contexto_historico = await self.context_retrieval.build_context_string(
            company_id=company_id, 
            project_id=project_id, 
            context_used=context_used,
            group_ids=group_ids
        )
        
        if contexto_historico:
            prompt += f"--- CONTEXTO HISTÓRICO (Relatórios Anteriores) ---\n{contexto_historico}\n\n"
        
        # 3. Adiciona instruções pontuais do usuário (se houver)
        if comentario_extra:
            prompt += f"--- INSTRUÇÕES ADICIONAIS DO USUÁRIO ---\n{comentario_extra}\n\n"
            
        # 4. Anexa o documento atual (ex: um word que o usuário acabou de subir)
        if texto_documento:
            prompt += f"--- DOCUMENTO ATUAL PARA ANÁLISE ---\n{texto_documento}\n\n"
        
        # Trava final de formatação
        prompt += "Gere o relatório final estruturado em formato Markdown."
        
        return prompt

    async def executar_analise(self, task_payload: dict, texto_extraido: str) -> str:
        """
        Função principal que orquestra a chamada do LLM consultando o AGENT_CONFIG.
        """
        job_id = task_payload.get('job_id')
        analysis_type = task_payload.get("analysis_type")
        logger.info(f"[AgentService] Iniciando análise para o job {job_id}")
        
        # 1. Monta o super prompt
        mega_prompt = await self._montar_prompt(
            texto_documento=texto_extraido,
            analysis_type=analysis_type,
            comentario_extra=task_payload.get("comentario_extra"),
            company_id=task_payload.get("company_id"),
            project_id=task_payload.get("project_id"),
            context_used=task_payload.get("context_used", {}), 
            group_ids=task_payload.get("group_ids")
        )
        
        # 2. 🚀 ROTEAMENTO DINÂMICO DA LLM (Usando o AGENT_CONFIG)
        config_agente = AGENT_CONFIG.get(analysis_type)
        if not config_agente:
            raise ValueError(f"Tipo de análise '{analysis_type}' não encontrado no AGENT_CONFIG.")

        nome_servico = config_agente.get("service")
        nome_modelo = config_agente.get("llm_model")

        # Buscamos a instância do serviço (injetada no __init__)
        llm_service = self.llm_services.get(nome_servico)
        if not llm_service:
            raise ValueError(f"Serviço LLM '{nome_servico}' não foi registrado no llm_services do AgentService.")

        logger.info(f"🧠 [AgentService] Delegando job {job_id} para o serviço '{nome_servico}' com modelo '{nome_modelo}'")

        # 3. Chama o serviço especialista passando o prompt final e qual modelo ele deve usar
        resposta_llm = await llm_service.gerar_texto(
            prompt=mega_prompt, 
            modelo=nome_modelo,
            company_id=task_payload.get("company_id"), 
            group_id=task_payload.get("group_ids")
        )
        
        return resposta_llm
