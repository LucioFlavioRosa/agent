import logging
from pathlib import Path
from typing import Optional
import re

# Supondo que você salvou o serviço que criamos no passo anterior neste caminho:
from backend.app.services.context_retrieval_service import ContextRetrievalService

logger = logging.getLogger("mcp_agent")

class AgentService:
    def __init__(self, context_retrieval_service: ContextRetrievalService, *args, **kwargs):
        """
        Inicializa o serviço do agente.
        Recebe o ContextRetrievalService injetado para buscar relatórios antigos no Blob Storage.
        """
        self.context_retrieval = context_retrieval_service
        
        # ... (Outras inicializações de clientes LLM, Azure OpenAI, etc que você já tinha) ...
        # self.llm_client = kwargs.get("llm_client")

    def _obter_prompt_base(self, analysis_type: Optional[str]) -> str:
        """
        Lê o arquivo Markdown correspondente ao tipo de análise na pasta 'prompts'.
        Este arquivo dita as regras de negócio e o comportamento geral da IA.
        """
        prompt_padrao = "Você é um assistente de IA corporativo. Faça uma análise do documento fornecido."
        
        if not analysis_type:
            return prompt_padrao

        # Sanitização contra Path Traversal
        nome_seguro = re.sub(r'[^a-zA-Z0-9_-]', '', analysis_type)
        
        # Descobre o caminho da pasta prompts (backend/app/prompts/)
        diretorio_base = Path(__file__).resolve().parent.parent
        caminho_arquivo = diretorio_base / "prompts" / f"{nome_seguro}.md"
        
        try:
            if caminho_arquivo.exists() and caminho_arquivo.is_file():
                logger.info(f"[AgentService] Carregando prompt base (comportamento) de: {caminho_arquivo.name}")
                return caminho_arquivo.read_text(encoding="utf-8")
            else:
                logger.warning(f"⚠️ [AgentService] Prompt base não encontrado: {caminho_arquivo.name}. Usando fallback.")
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

    # ------------------------------------------------------------------------
    # EXEMPLO DE COMO SUAS FUNÇÕES PRINCIPAIS DEVERÃO CHAMAR O _montar_prompt
    # ------------------------------------------------------------------------
    
    async def executar_analise(self, task_payload: dict, texto_extraido: str) -> str:
        """
        Função principal que orquestra a chamada do LLM.
        """
        logger.info(f"[AgentService] Iniciando análise para o job {task_payload.get('job_id')}")
        
        # 1. Monta o super prompt (ATENÇÃO: Agora com o 'await'!)
        mega_prompt = await self._montar_prompt(
            texto_documento=texto_extraido,
            analysis_type=task_payload.get("analysis_type"),
            comentario_extra=task_payload.get("comentario_extra"),
            company_id=task_payload.get("company_id"),
            project_id=task_payload.get("project_id"),
            context_used=task_payload.get("context_used", {}), # Injeta o contexto da fila!
            group_ids=task_payload.get("group_ids")
        )
        
        # 2. Chama o LLM (Azure OpenAI, por exemplo)
        # resposta_llm = await self._chamar_llm(mega_prompt)
        # return resposta_llm
        
        return mega_prompt # Retornando o prompt apenas para fins didáticos neste exemplo
