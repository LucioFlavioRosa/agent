import logging
from pathlib import Path
from typing import Optional
import re

logger = logging.getLogger("mcp_agent")

class AgentService:
    # ... (seu __init__ continua igual) ...

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

    def _obter_contexto_especifico(self, company_id: str, project_id: str) -> str:
        """
        [PLACEHOLDER]
        Aqui entrará a lógica que você vai explicar depois.
        Vai buscar relatórios gerados em outros momentos (ex: no Blob Storage ou Banco de Dados)
        para dar contexto histórico à IA.
        """
        # Por enquanto retorna vazio, aguardando sua implementação futura
        return ""

    def _montar_prompt(
        self, 
        texto_documento: str, 
        analysis_type: Optional[str], 
        comentario_extra: Optional[str],
        company_id: str,
        project_id: str
    ) -> str:
        """
        Monta o Mega-Prompt final juntando todas as camadas (Base + Histórico + Extras + Documento atual).
        """
        # 1. Carrega as regras de comportamento (.md)
        prompt = self._obter_prompt_base(analysis_type)
        prompt += "\n\n"
        
        # 2. Carrega o histórico (relatórios anteriores, se existirem)
        contexto_historico = self._obter_contexto_especifico(company_id, project_id)
        if contexto_historico:
            prompt += f"--- CONTEXTO HISTÓRICO (Relatórios Anteriores) ---\n{contexto_historico}\n\n"
        
        # 3. Adiciona instruções pontuais do usuário
        if comentario_extra:
            prompt += f"--- INSTRUÇÕES ADICIONAIS DO USUÁRIO ---\n{comentario_extra}\n\n"
            
        # 4. Anexa o documento extraído para análise
        prompt += f"--- DOCUMENTO ATUAL PARA ANÁLISE ---\n{texto_documento}\n\n"
        
        prompt += "Gere o relatório final estruturado em formato Markdown."
        
        return prompt

    # ... (o resto das funções _chamar_llm e executar_analise continuam iguais) ...
