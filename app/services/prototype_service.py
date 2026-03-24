import re
import asyncio
import logging
import traceback
import json
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
        
        self.audit_service = LLMAuditService(self.blob_storage.vault_service)

    def _obter_prompt_base(self, analysis_type: Optional[str]) -> str:
        prompt_padrao = (
            "Você é um Desenvolvedor Frontend Sênior. Crie um protótipo em HTML/CSS/JS (Single File). "
            "Utilize a biblioteca Tailwind CSS via CDN para estilização."
        )
        
        if not analysis_type or analysis_type not in AGENT_CONFIG:
            print("⚠️ [PROMPT BASE] 'analysis_type' não fornecido ou não mapeado. Usando prompt padrão em memória.", flush=True)
            return prompt_padrao
            
        nome_arquivo_prompt = AGENT_CONFIG[analysis_type]["prompt_file"]
        diretorio_base = Path(__file__).resolve().parent.parent
        caminho_arquivo = diretorio_base / "prompts" / nome_arquivo_prompt
        
        try:
            if caminho_arquivo.exists() and caminho_arquivo.is_file():
                conteudo = caminho_arquivo.read_text(encoding="utf-8")
                print(f"✅ [PROMPT BASE] Arquivo de instrução lido com sucesso: 'prompts/{nome_arquivo_prompt}' (Tamanho: {len(conteudo)} chars)", flush=True)
                return conteudo
            else:
                print(f"⚠️ [PROMPT BASE] Arquivo 'prompts/{nome_arquivo_prompt}' não encontrado fisicamente. Usando prompt padrão em memória.", flush=True)
                return prompt_padrao
        except Exception as e:
            print(f"❌ [ERRO] Falha ao ler arquivo de prompt base 'prompts/{nome_arquivo_prompt}': {e}", flush=True)
            traceback.print_exc()
            logger.log_erro("erro_leitura_prompt_base", f"Erro ao ler prompt: {e}")
            return prompt_padrao

    def _obter_template_empresa(self, company_template: Optional[str]) -> str:
        print(f"\n🔍 [DEBUG TEMPLATE] Iniciando busca por template...", flush=True)
        print(f"   -> Valor recebido do payload (company_template): '{company_template}'", flush=True)
        
        if not company_template or str(company_template).strip() == "" or str(company_template).lower() == "none":
            print(f"   -> Nenhum template selecionado no front. Seguindo com design padrão.", flush=True)
            return ""
            
        nome_arquivo = str(company_template).strip().lower().replace(" ", "")
        if not nome_arquivo.endswith(".md"):
            nome_arquivo += ".md"
            
        diretorio_base = Path(__file__).resolve().parent.parent
        pasta_templates = diretorio_base / "templates"
        caminho_arquivo = pasta_templates / nome_arquivo
        
        try:
            if pasta_templates.exists() and pasta_templates.is_dir():
                arquivos_na_pasta = [f.name for f in pasta_templates.iterdir() if f.is_file()]
                print(f"   -> Arquivos encontrados dentro da pasta 'templates': {arquivos_na_pasta}", flush=True)
            else:
                print(f"   -> ⚠️ AVISO: A pasta 'templates' NÃO EXISTE fisicamente no servidor!", flush=True)

            if caminho_arquivo.exists() and caminho_arquivo.is_file():
                conteudo = caminho_arquivo.read_text(encoding="utf-8")
                print(f"✅ [TEMPLATE] Design System de '{nome_arquivo}' injetado com sucesso! (Tamanho: {len(conteudo)} chars)", flush=True)
                return conteudo
            else:
                print(f"⚠️ [TEMPLATE] Arquivo '{nome_arquivo}' não encontrado. O protótipo será gerado sem template.", flush=True)
                return ""
        except Exception as e:
            print(f"❌ [ERRO TEMPLATE] Falha ao ler template {nome_arquivo}: {e}", flush=True)
            traceback.print_exc()
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
        company_template: Optional[str] = None,
        target_epic_id: Optional[str] = None 
    ) -> str:
        
        print(f"\n{'='*60}\n🔍 [DEBUG PROTÓTIPO] MONTAGEM DO PROMPT\n{'='*60}", flush=True)
        
        prompt = self._obter_prompt_base(analysis_type)
        
        is_reviewer = analysis_type and "reviwer" in str(analysis_type).lower()
        is_fromepic = analysis_type and "fromepic" in str(analysis_type).lower()
        
        if (is_reviewer or is_fromepic) and context_used:
            print(f"📌 Chaves de contexto originais no Banco: {list(context_used.keys())}", flush=True)
            
            # 🚀 A MÁGICA: Filtramos a tag do Épico APENAS para não quebrar o download do Blob!
            # O Banco de Dados continua intacto.
            context_para_baixar = {k: v for k, v in context_used.items() if k != "target_epic_id"}
            
            # Formata os logs visualmente para 'epics.md' etc
            nomes_arquivos_contexto = [k.replace('_job_id', '.md') for k in context_para_baixar.keys()]
            print(f"📌 [CONTEXTO] Solicitando download dos arquivos base: {nomes_arquivos_contexto}", flush=True)
            
            context_result = self.context_retrieval.build_context_string(
                company_id=company_id, 
                project_id=project_id, 
                context_used=context_para_baixar, # <-- Passamos o contexto limpo para o downloader!
                group_ids=group_ids
            )
            
            codigo_html_anterior = await context_result if asyncio.iscoroutine(context_result) else context_result
            
            if codigo_html_anterior:
                print(f"✅ [CONTEXTO] Arquivos {nomes_arquivos_contexto} lidos com sucesso! (Tamanho: {len(codigo_html_anterior)} chars)", flush=True)
                
                if is_fromepic and target_epic_id:
                    prompt += f"\n\n🎯 ALVO DO PROTÓTIPO: ATENÇÃO MÁXIMA!\n"
                    prompt += f"Você deve criar a interface EXCLUSIVAMENTE baseada no Épico de Identificador '{target_epic_id}'.\n"
                    prompt += f"Abaixo está o relatório contendo todos os épicos do projeto. Procure pelo épico '{target_epic_id}' e use os dados dele (Título, Business Case, Entregáveis Macro, etc) para projetar e compor a tela. Ignore completamente as informações dos outros épicos.\n\n"
                    prompt += f"--- RELATÓRIO DE ÉPICOS ---\n{codigo_html_anterior}\n\n"
                else:
                    prompt += f"\n\n--- CÓDIGO DO PROTÓTIPO DE REFERÊNCIA (CONFORME CONTEXTO) ---\n{codigo_html_anterior}\n\n"

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
        
        return prompt
        
    async def executar_analise(self, task_payload: dict, texto_instrucoes: str, texto_identidade: str) -> str:
        job_id = task_payload.get('job_id')
        analysis_type = task_payload.get("analysis_type")
        company_id = task_payload.get("company_id")
        project_id = task_payload.get("project_id")
        group_ids = task_payload.get("group_ids")
        user_email = task_payload.get("email", "email_nao_fornecido") 
        company_template = task_payload.get("company_template")
        target_epic_id = task_payload.get("target_epic_id")
        
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
                company_template=company_template,
                target_epic_id=target_epic_id 
            )
            
            # =========================================================
            # 📊 LOG DE TAMANHO (RESTRIÇÃO REMOVIDA)
            # =========================================================
            tamanho_prompt = len(mega_prompt)
            tokens_estimados = tamanho_prompt // 4
            
            print(f"📏 [VERIFICAÇÃO DE TAMANHO] Mega Prompt possui {tamanho_prompt} caracteres (~{tokens_estimados} tokens).", flush=True)
            # =========================================================
            
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
            
            # =========================================================
            # 🚀 TRAVA DE SEGURANÇA 2: LIMITE DE TOKENS DE SAÍDA (RESPOSTA TRUNCADA)
            # =========================================================
            if out_tokens >= 40000: 
                mensagem_corte = (
                    "A interface solicitada é muito complexa e a inteligência artificial atingiu o limite "
                    "máximo de escrita, deixando o código HTML pela metade. "
                    "Para evitar uma tela quebrada, a geração foi interrompida. Tente solicitar uma versão "
                    "mais simples ou foque em apenas uma funcionalidade por vez. Se os detalhes forem mandatórios, você terá que construir paginas separadas a partir da ultima versão do prototipo "
                )
                print(f"⚠️ [BLOQUEIO DE OUTPUT] O HTML foi truncado com {out_tokens} tokens. Abortando salvamento.", flush=True)
                raise ValueError(mensagem_corte)
            # =========================================================

            # --- LIMPEZA BÁSICA ---
            if "```html" in resposta_llm:
                resposta_llm = resposta_llm.replace("```html", "")
            if "```" in resposta_llm:
                resposta_llm = resposta_llm.replace("```", "")
            resposta_llm = resposta_llm.strip()

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
                print(f"✅ Arquivo salvo com sucesso.", flush=True)

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
            
        except ValueError as ve:
            raise ve
        except Exception as e:
            print(f"❌ [ERRO CRÍTICO] Falha na execução da IA: {str(e)}", flush=True)
            traceback.print_exc()
            raise
            traceback.print_exc()
            raise
