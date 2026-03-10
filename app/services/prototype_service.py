import re
import asyncio
import logging
import traceback
from pathlib import Path
from typing import Optional

from app.services.context_retrieval_service import ContextRetrievalService
from app.services.blob_storage_service import BlobStorageService
from app.config.agent_mapping import AGENT_CONFIG
from app.utils.log_formatter import StructuredLogger

logger = StructuredLogger("agent_prototype_service")

class AgentService:
    def __init__(
        self, 
        context_retrieval_service: ContextRetrievalService, 
        blob_storage_service: BlobStorageService, 
        llm_services: dict, 
        *args, **kwargs
    ):
        self.context_retrieval = context_retrieval_service
        self.blob_storage = blob_storage_service
        self.llm_services = llm_services

    def _obter_prompt_base(self, analysis_type: Optional[str]) -> str:
        """Busca o arquivo de prompt (.md) na pasta de prompts do MCP"""
        prompt_padrao = (
            "Você é um Desenvolvedor Frontend Sênior. Crie um protótipo em HTML/CSS/JS (Single File). "
            "Utilize a biblioteca Tailwind CSS via CDN para estilização."
        )
        
        if not analysis_type or analysis_type not in AGENT_CONFIG:
            return prompt_padrao
            
        nome_arquivo_prompt = AGENT_CONFIG[analysis_type]["prompt_file"]
        diretorio_base = Path(__file__).resolve().parent.parent
        caminho_arquivo = diretorio_base / "prompts" / nome_arquivo_prompt
        
        try:
            if caminho_arquivo.exists() and caminho_arquivo.is_file():
                return caminho_arquivo.read_text(encoding="utf-8")
            return prompt_padrao
        except Exception as e:
            # Log detalhado para erro de leitura de arquivo
            print(f"❌ [ERRO] Falha ao ler arquivo de prompt: {e}", flush=True)
            traceback.print_exc()
            logger.log_erro("erro_leitura_prompt_base", f"Erro ao ler prompt: {e}")
            return prompt_padrao

    async def _montar_prompt(
        self, 
        texto_instrucoes: str, 
        texto_identidade: str, 
        analysis_type: Optional[str], 
        comentario_extra: Optional[str],
        company_id: str,
        project_id: str,
        context_used: dict,
        group_ids: Optional[str] = None
    ) -> str:
        """Une todas as peças de informação para enviar à IA"""
        
        print(f"\n{'='*60}\n🔍 [DEBUG PROTÓTIPO] MONTAGEM DO PROMPT\n{'='*60}", flush=True)
        
        # 1. Instruções do Sistema (O arquivo .md da pasta prompts)
        prompt = self._obter_prompt_base(analysis_type)

        # 2. Recuperação de Contexto (Baseada nos Job IDs enviados no payload)
        # O sistema verifica se o agente é de revisão/refinamento
        is_reviewer = analysis_type and "reviwer" in str(analysis_type).lower()
        
        if is_reviewer and context_used:
            print(f"📌 Chaves de contexto para refinamento (Linhagem): {list(context_used.keys())}", flush=True)
            
            # 🚀 O ContextRetrievalService utiliza os job_ids contidos no 'context_used'
            # para localizar e ler os arquivos específicos (HTMLs anteriores) no Blob Storage.
            context_result = self.context_retrieval.build_context_string(
                company_id=company_id, 
                project_id=project_id, 
                context_used=context_used,
                group_ids=group_ids
            )
            
            # Verifica se o retorno precisa de await
            codigo_html_anterior = await context_result if asyncio.iscoroutine(context_result) else context_result
            
            if codigo_html_anterior:
                prompt += f"\n\n--- CÓDIGO DO PROTÓTIPO DE REFERÊNCIA (CONFORME CONTEXTO) ---\n{codigo_html_anterior}\n\n"

        # 3. Instruções do DOCX 1 (Negócio/Telas)
        if texto_instrucoes:
            prompt += f"--- REQUISITOS DE TELA E NEGÓCIO ---\n{texto_instrucoes}\n\n"

        # 4. Instruções do DOCX 2 (Identidade Visual/Design System)
        if texto_identidade:
            prompt += f"--- DIRETRIZES DE ESTILO E CORES ---\n{texto_identidade}\n\n"

        # 5. Comentário do usuário (Prompt direto do chat)
        if comentario_extra:
            prompt += f"--- SOLICITAÇÃO ESPECÍFICA DO USUÁRIO ---\n{comentario_extra}\n\n"
            
        prompt += "\nRETORNE APENAS O CÓDIGO HTML COMPLETO, SEM EXPLICAÇÕES."
        
        print(f"🚀 Mega Prompt montado com {len(prompt)} caracteres.", flush=True)
        return prompt

    async def executar_analise(self, task_payload: dict, texto_instrucoes: str, texto_identidade: str) -> str:
        """Executa a chamada à IA e salva o arquivo HTML final"""
        job_id = task_payload.get('job_id')
        analysis_type = task_payload.get("analysis_type")
        company_id = task_payload.get("company_id")
        project_id = task_payload.get("project_id")
        group_ids = task_payload.get("group_ids")
        
        try:
            # Montagem
            mega_prompt = await self._montar_prompt(
                texto_instrucoes=texto_instrucoes,
                texto_identidade=texto_identidade,
                analysis_type=analysis_type,
                comentario_extra=task_payload.get("comentario_extra"),
                company_id=company_id,
                project_id=project_id,
                context_used=task_payload.get("context_used", {}), 
                group_ids=group_ids
            )
            
            config_agente = AGENT_CONFIG.get(analysis_type, {})
            nome_servico = config_agente.get("service")
            nome_modelo = config_agente.get("llm_model")
            nome_arquivo_saida = config_agente.get("output_filename", "index.html")
            
            llm_service = self.llm_services.get(nome_servico)
            
            print(f"📡 Chamando {nome_servico}...", flush=True)

            resposta_llm = await llm_service.gerar_texto(
                prompt=mega_prompt, 
                modelo=nome_modelo,
                company_id=company_id, 
                group_id=group_ids
            )
            
            # --- LIMPEZA BÁSICA ---
            if "```html" in resposta_llm:
                resposta_llm = resposta_llm.replace("```html", "")
            if "```" in resposta_llm:
                resposta_llm = resposta_llm.replace("```", "")
            
            resposta_llm = resposta_llm.strip()
            # ----------------------

            # Salvar no Blob Storage
            if resposta_llm and nome_arquivo_saida:
                file_bytes = resposta_llm.encode('utf-8')
                await self.blob_storage.save_document(
                    company_id=company_id,
                    project_id=project_id,
                    job_id=job_id,
                    file_data=file_bytes,
                    filename=nome_arquivo_saida,
                    group_id=group_ids
                )
                print(f"✅ HTML salvo com sucesso.", flush=True)
                
            return resposta_llm
            
        except Exception as e:
            # Agora exibe o erro e o rastro completo (Stack Trace) nos logs da Azure
            print(f"❌ [ERRO CRÍTICO] Falha na execução da IA: {str(e)}", flush=True)
            traceback.print_exc()
            raise
