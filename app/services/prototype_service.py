import re
import asyncio
import logging
import traceback
from pathlib import Path
from typing import Optional

from app.services.context_retrieval_service import ContextRetrievalService
from app.services.blob_storage_service import BlobStorageService
from app.services.llm_audit_service import LLMAuditService 
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
        
        # 🚀 Instanciando o serviço de auditoria usando as credenciais do Vault
        self.audit_service = LLMAuditService(self.blob_storage.vault_service)

    def _obter_prompt_base(self, analysis_type: Optional[str]) -> str:
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
            print(f"❌ [ERRO] Falha ao ler arquivo de prompt: {e}", flush=True)
            traceback.print_exc()
            logger.log_erro("erro_leitura_prompt_base", f"Erro ao ler prompt: {e}")
            return prompt_padrao

    # 🚀 NOVA FUNÇÃO: Leitor dinâmico da pasta templates
    def _obter_template_empresa(self, company_template: Optional[str]) -> str:
        if not company_template:
            return ""
            
        # Normaliza o nome (ex: "Porto Seguro" vira "portoseguro.md")
        nome_arquivo = str(company_template).strip().lower().replace(" ", "")
        if not nome_arquivo.endswith(".md"):
            nome_arquivo += ".md"
            
        diretorio_base = Path(__file__).resolve().parent.parent
        caminho_arquivo = diretorio_base / "templates" / nome_arquivo
        
        try:
            if caminho_arquivo.exists() and caminho_arquivo.is_file():
                print(f"🎨 [TEMPLATE] Injetando Design System de '{nome_arquivo}'", flush=True)
                return caminho_arquivo.read_text(encoding="utf-8")
            else:
                print(f"⚠️ [TEMPLATE] Arquivo '{nome_arquivo}' não encontrado na pasta templates.", flush=True)
                return ""
        except Exception as e:
            print(f"❌ [ERRO] Falha ao ler template {nome_arquivo}: {e}", flush=True)
            return ""

    async def _montar_prompt(
        self, 
        texto_instrucoes: str, 
        texto_identidade: str, 
        analysis_type: Optional[str], 
        comentario_extra: Optional[str],
        company_id: str,
        project_id: str,
        context_used: dict,
        group_ids: Optional[str] = None,
        company_template: Optional[str] = None # 🚀 NOVO PARÂMETRO OPCIONAL
    ) -> str:
        
        print(f"\n{'='*60}\n🔍 [DEBUG PROTÓTIPO] MONTAGEM DO PROMPT\n{'='*60}", flush=True)
        
        prompt = self._obter_prompt_base(analysis_type)
        is_reviewer = analysis_type and "reviwer" in str(analysis_type).lower()
        
        if is_reviewer and context_used:
            print(f"📌 Chaves de contexto para refinamento (Linhagem): {list(context_used.keys())}", flush=True)
            
            context_result = self.context_retrieval.build_context_string(
                company_id=company_id, 
                project_id=project_id, 
                context_used=context_used,
                group_ids=group_ids
            )
            
            codigo_html_anterior = await context_result if asyncio.iscoroutine(context_result) else context_result
            
            if codigo_html_anterior:
                prompt += f"\n\n--- CÓDIGO DO PROTÓTIPO DE REFERÊNCIA (CONFORME CONTEXTO) ---\n{codigo_html_anterior}\n\n"

        # 🚀 INJETANDO AS DIRETRIZES DA EMPRESA SE EXISTIREM
        texto_template = self._obter_template_empresa(company_template)
        if texto_template:
            prompt += f"--- DIRETRIZES DE UI/UX DA EMPRESA ({str(company_template).upper()}) ---\n{texto_template}\n\n"

        if texto_instrucoes:
            prompt += f"--- REQUISITOS DE TELA E NEGÓCIO ---\n{texto_instrucoes}\n\n"

        if texto_identidade:
            prompt += f"--- DIRETRIZES DE ESTILO E CORES (ARQUIVO EXTRA) ---\n{texto_identidade}\n\n"

        if comentario_extra:
            prompt += f"--- SOLICITAÇÃO ESPECÍFICA DO USUÁRIO ---\n{comentario_extra}\n\n"
            
        prompt += "\nRETORNE APENAS O CÓDIGO HTML COMPLETO, SEM EXPLICAÇÕES."
        
        print(f"🚀 Mega Prompt montado com {len(prompt)} caracteres.", flush=True)
        return prompt

    async def executar_analise(self, task_payload: dict, texto_instrucoes: str, texto_identidade: str) -> str:
        job_id = task_payload.get('job_id')
        analysis_type = task_payload.get("analysis_type")
        company_id = task_payload.get("company_id")
        project_id = task_payload.get("project_id")
        group_ids = task_payload.get("group_ids")
        user_email = task_payload.get("email", "email_nao_fornecido") 
        company_template = task_payload.get("company_template") # 🚀 RESGATA DO PAYLOAD
        
        try:
            mega_prompt = await self._montar_prompt(
                texto_instrucoes=texto_instrucoes,
                texto_identidade=texto_identidade,
                analysis_type=analysis_type,
                comentario_extra=task_payload.get("comentario_extra"),
                company_id=company_id,
                project_id=project_id,
                context_used=task_payload.get("context_used", {}), 
                group_ids=group_ids,
                company_template=company_template # 🚀 REPASSA PARA O MONTADOR DE PROMPT
            )
            
            config_agente = AGENT_CONFIG.get(analysis_type, {})
            nome_servico = config_agente.get("service")
            nome_modelo = config_agente.get("llm_model")
            nome_arquivo_saida = config_agente.get("output_filename", "index.html")
            
            llm_service = self.llm_services.get(nome_servico)
            
            print(f"📡 Chamando {nome_servico}...", flush=True)

            resposta_llm, in_tokens, out_tokens = await llm_service.gerar_texto(
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

            # 1. Salvar HTML no Blob Storage
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

            # 🚀 2. SALVAR AUDITORIA/MÉTRICAS USANDO O NOVO SERVIÇO 🚀
            await self.audit_service.save_usage_metrics(
                company_id=company_id,
                project_id=project_id,
                job_id=job_id,
                user_email=user_email,
                analysis_type=analysis_type,
                model_name=nome_modelo,
                input_tokens=in_tokens,
                output_tokens=out_tokens,
                group_ids=group_ids
            )

            return resposta_llm
            
        except Exception as e:
            print(f"❌ [ERRO CRÍTICO] Falha na execução da IA: {str(e)}", flush=True)
            traceback.print_exc()
            raise
