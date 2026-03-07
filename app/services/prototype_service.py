import logging
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
        prompt_padrao = "Você é um Desenvolvedor Frontend Sênior. Crie um protótipo em HTML/CSS/JS (Single File)."
        logger.log_evento("INFO", "_obter_prompt_base", "Obtendo prompt base", extra={"analysis_type": analysis_type})
        
        if not analysis_type or analysis_type not in AGENT_CONFIG:
            logger.log_info_negocio("prompt_fallback", "Agente não mapeado, usando prompt padrão.", extra={"analysis_type": analysis_type})
            return prompt_padrao
            
        nome_arquivo_prompt = AGENT_CONFIG[analysis_type]["prompt_file"]
        diretorio_base = Path(__file__).resolve().parent.parent
        caminho_arquivo = diretorio_base / "prompts" / nome_arquivo_prompt
        
        try:
            if caminho_arquivo.exists() and caminho_arquivo.is_file():
                logger.log_info_negocio("prompt_base_encontrado", f"Prompt base encontrado: {caminho_arquivo.name}", extra={"analysis_type": analysis_type})
                return caminho_arquivo.read_text(encoding="utf-8")
            else:
                logger.log_info_negocio("prompt_base_nao_encontrado", f"Prompt '{caminho_arquivo.name}' não encontrado.", extra={"analysis_type": analysis_type})
                return prompt_padrao
        except Exception as e:
            logger.log_erro("erro_leitura_prompt_base", f"Erro ao ler prompt base: {e}", extra={"analysis_type": analysis_type})
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
        logger.log_evento("INFO", "_montar_prompt", "Montando mega-prompt", extra={"analysis_type": analysis_type})
        
        print(f"\n{'='*60}\n🔍 [DEBUG PROTÓTIPO] INICIANDO MONTAGEM DO MEGA PROMPT\n{'='*60}", flush=True)
        print(f"📌 Agente acionado: {analysis_type}", flush=True)
        
        # 1. LÊ O PROMPT PADRÃO (Da pasta /prompts)
        prompt = self._obter_prompt_base(analysis_type)
        print(f"✅ Prompt base lido com sucesso (Tamanho: {len(prompt)} chars)", flush=True)

        # 2. LÊ O CONTEXTO ANTERIOR APENAS SE FOR REFINAMENTO
        # A palavra 'reviwer' indica que é uma revisão/refinamento
        is_reviewer = "reviwer" in str(analysis_type).lower()
        
        if is_reviewer and context_used:
            print(f"📌 Chaves de contexto para refinamento: {list(context_used.keys())}", flush=True)
            codigo_html_anterior = await self.context_retrieval.build_context_string(
                company_id=company_id, 
                project_id=project_id, 
                context_used=context_used,
                group_ids=group_ids
            )
            
            if codigo_html_anterior:
                print(f"✅ CÓDIGO HTML ANTERIOR BAIXADO COM SUCESSO! (Tamanho: {len(codigo_html_anterior)} chars)", flush=True)
                prompt += f"\n\n--- CÓDIGO DO PROTÓTIPO ANTERIOR (PARA REFINAR) ---\nUse este HTML como base e aplique as melhorias solicitadas:\n{codigo_html_anterior}\n\n"
            else:
                print(f"⚠️ AVISO: Não foi possível carregar o HTML anterior.", flush=True)

        # 3. LÊ O ARQUIVO DE INSTRUÇÕES GERAIS (DOCX)
        if texto_instrucoes:
            prompt += f"--- INSTRUÇÕES GERAIS DE NEGÓCIO E TELA ---\n{texto_instrucoes}\n\n"
            print(f"✅ Arquivo de Instruções Gerais anexado (Tamanho: {len(texto_instrucoes)} chars).", flush=True)

        # 4. LÊ O ARQUIVO DE IDENTIDADE VISUAL/ESTILO (DOCX)
        if texto_identidade:
            prompt += f"--- DIRETRIZES DE ESTILO E IDENTIDADE VISUAL ---\nSiga estritamente estas regras:\n{texto_identidade}\n\n"
            print(f"✅ Arquivo de Identidade Visual anexado (Tamanho: {len(texto_identidade)} chars).", flush=True)

        # 5. LÊ O PROMPT/COMENTÁRIO DIGITADO PELO USUÁRIO
        if comentario_extra:
            prompt += f"--- INSTRUÇÃO DO USUÁRIO (PROMPT ATUAL) ---\n{comentario_extra}\n\n"
            print(f"✅ Instruções do usuário (Prompt) anexadas.", flush=True)
            
        # Garante que a IA não mande markdown ```html antes do código se você quiser apenas o arquivo cru
        prompt += "\nRETORNE APENAS O CÓDIGO HTML COMPLETO. NÃO ADICIONE NENHUMA EXPLICAÇÃO ANTES OU DEPOIS DO CÓDIGO."
        
        print(f"\n🚀 MEGA PROMPT FINALIZADO! Tamanho total: {len(prompt)} caracteres.", flush=True)
        print(f"{'='*60}\n", flush=True)
        
        return prompt

    async def executar_analise(self, task_payload: dict, texto_instrucoes: str, texto_identidade: str) -> str:
        job_id = task_payload.get('job_id')
        analysis_type = task_payload.get("analysis_type")
        company_id = task_payload.get("company_id")
        project_id = task_payload.get("project_id")
        group_ids = task_payload.get("group_ids")
        
        logger.log_info_negocio("inicio_executar_analise", "Início da análise IA para Protótipo", job_id=job_id, company_id=company_id, extra={"analysis_type": analysis_type})
        
        try:
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
            
            config_agente = AGENT_CONFIG.get(analysis_type)
            if not config_agente:
                raise ValueError(f"Tipo '{analysis_type}' não encontrado no AGENT_CONFIG.")
                
            nome_servico = config_agente.get("service")
            nome_modelo = config_agente.get("llm_model")
            
            # 🚀 O NOME DO ARQUIVO VEM DO AGENT_CONFIG ("index.html")
            nome_arquivo_saida = config_agente.get("output_filename", "index.html")
            
            llm_service = self.llm_services.get(nome_servico)
            if not llm_service:
                raise ValueError(f"Serviço LLM '{nome_servico}' não foi registrado no llm_services.")
                
            logger.log_info_negocio("chamada_llm", "Chamando LLM.", job_id=job_id, extra={"modelo": nome_modelo})
            print(f"\n📡 DISPARANDO REQUISIÇÃO PARA {nome_servico} ({nome_modelo})...", flush=True)

            resposta_llm = await llm_service.gerar_texto(
                prompt=mega_prompt, 
                modelo=nome_modelo,
                company_id=company_id, 
                group_id=group_ids
            )
            
            # Limpeza do resultado (Às vezes o Claude retorna ```html no começo e ``` no final)
            if resposta_llm.startswith("```html"):
                resposta_llm = resposta_llm.replace("```html", "", 1)
            if resposta_llm.endswith("```"):
                resposta_llm = resposta_llm[:resposta_llm.rfind("```")]
            resposta_llm = resposta_llm.strip()

            print(f"✅ CÓDIGO HTML RECEBIDO DO LLM! (Tamanho: {len(resposta_llm)} chars)", flush=True)

            # Salvar no Blob Storage
            if resposta_llm and nome_arquivo_saida:
                file_bytes = resposta_llm.encode('utf-8')
                caminho_blob = await self.blob_storage.save_document(
                    company_id=company_id,
                    project_id=project_id,
                    job_id=job_id,
                    file_data=file_bytes,
                    filename=nome_arquivo_saida,
                    group_id=group_ids
                )
                logger.log_info_negocio("blob_salvo", f"HTML salvo em: {caminho_blob}", job_id=job_id)
                
            return resposta_llm
            
        except Exception as e:
            logger.log_erro("erro_executar_analise", f"Erro crítico na geração: {e}", job_id=job_id)
            print(f"\n❌ ERRO CRÍTICO NA EXECUÇÃO DA IA: {str(e)}", flush=True)
            raise
