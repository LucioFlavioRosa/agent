import logging
from pathlib import Path
from typing import Optional
import re

from backend.app.services.context_retrieval_service import ContextRetrievalService
from backend.app.services.blob_storage_service import BlobStorageService
from backend.app.config.agent_mapping import AGENT_CONFIG
from backend.app.utils.log_formatter import StructuredLogger

logger = StructuredLogger("agent_service")

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
        prompt_padrao = "Você é um assistente de IA corporativo. Faça uma análise do documento fornecido."
        logger.log_entrada_funcao("_obter_prompt_base", mensagem="Obtendo prompt base", extra={"analysis_type": analysis_type})
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
                logger.log_info_negocio("prompt_base_nao_encontrado", f"Prompt '{caminho_arquivo.name}' não encontrado, usando padrão.", extra={"analysis_type": analysis_type})
                return prompt_padrao
        except Exception as e:
            logger.log_erro("erro_leitura_prompt_base", f"Erro ao ler prompt base: {e}", extra={"analysis_type": analysis_type})
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
        logger.log_entrada_funcao("_montar_prompt", job_id=None, company_id=company_id, project_id=project_id, mensagem="Montando mega-prompt", extra={"analysis_type": analysis_type})
        
        # 🚀 INÍCIO DO DEBUG VISUAL
        print(f"\n{'='*60}\n🔍 [DEBUG AGENTE] INICIANDO MONTAGEM DO MEGA PROMPT\n{'='*60}", flush=True)
        print(f"📌 Agente acionado: {analysis_type}", flush=True)
        print(f"📌 Chaves de contexto recebidas do Redis/Fila: {list(context_used.keys())}", flush=True)
        
        prompt = self._obter_prompt_base(analysis_type)
        print(f"✅ Prompt base lido com sucesso (Tamanho: {len(prompt)} chars)", flush=True)

        contexto_historico = await self.context_retrieval.build_context_string(
            company_id=company_id, 
            project_id=project_id, 
            context_used=context_used,
            group_ids=group_ids
        )
        
        if contexto_historico:
            print(f"✅ CONTEXTO HISTÓRICO BAIXADO COM SUCESSO! (Tamanho: {len(contexto_historico)} chars)", flush=True)
            prompt += f"\n\n--- CONTEXTO HISTÓRICO (Relatórios Anteriores) ---\n{contexto_historico}\n\n"
        else:
            print(f"⚠️ AVISO: O Contexto Histórico retornou VAZIO! Se o agente precisar de épicos, ele vai falhar.", flush=True)

        if comentario_extra:
            prompt += f"--- INSTRUÇÕES ADICIONAIS DO USUÁRIO ---\n{comentario_extra}\n\n"
            print(f"✅ Instruções adicionais anexadas.", flush=True)

        if texto_documento:
            prompt += f"--- DOCUMENTO ATUAL PARA ANÁLISE ---\n{texto_documento}\n\n"
            print(f"✅ Documento DOCX anexado (Tamanho: {len(texto_documento)} chars).", flush=True)

        prompt += "Gere o relatório final estruturado em formato Markdown."
        
        print(f"\n🚀 MEGA PROMPT FINALIZADO! Tamanho total: {len(prompt)} caracteres.", flush=True)
        print(f"{'='*60}\n", flush=True)
        
        logger.log_saida_funcao("_montar_prompt", job_id=None, company_id=company_id, project_id=project_id, mensagem="Mega-prompt montado")
        return prompt

    async def executar_analise(self, task_payload: dict, texto_extraido: str) -> str:
        job_id = task_payload.get('job_id')
        analysis_type = task_payload.get("analysis_type")
        company_id = task_payload.get("company_id")
        project_id = task_payload.get("project_id")
        group_ids = task_payload.get("group_ids")
        
        logger.log_entrada_funcao("executar_analise", job_id=job_id, company_id=company_id, project_id=project_id, mensagem="Início da análise IA", extra={"analysis_type": analysis_type})
        
        try:
            mega_prompt = await self._montar_prompt(
                texto_documento=texto_extraido,
                analysis_type=analysis_type,
                comentario_extra=task_payload.get("comentario_extra"),
                company_id=company_id,
                project_id=project_id,
                context_used=task_payload.get("context_used", {}), 
                group_ids=group_ids
            )
            
            config_agente = AGENT_CONFIG.get(analysis_type)
            if not config_agente:
                logger.log_erro("tipo_analise_nao_encontrado", f"Tipo de análise '{analysis_type}' não encontrado no AGENT_CONFIG.", job_id=job_id, company_id=company_id, project_id=project_id)
                raise ValueError(f"Tipo de análise '{analysis_type}' não encontrado no AGENT_CONFIG.")
                
            nome_servico = config_agente.get("service")
            nome_modelo = config_agente.get("llm_model")
            nome_arquivo_saida = config_agente.get("output_filename")
            
            llm_service = self.llm_services.get(nome_servico)
            if not llm_service:
                logger.log_erro("servico_llm_nao_registrado", f"Serviço LLM '{nome_servico}' não foi registrado.", job_id=job_id, company_id=company_id, project_id=project_id)
                raise ValueError(f"Serviço LLM '{nome_servico}' não foi registrado no llm_services.")
                
            logger.log_info_negocio("chamada_llm", f"Chamando LLM para gerar resposta.", job_id=job_id, company_id=company_id, project_id=project_id, extra={"servico": nome_servico, "modelo": nome_modelo})
            
            # 🚀 IMPRESSÃO DEFINITIVA ANTES DE ENVIAR PARA A AWS
            print(f"\n📡 DISPARANDO REQUISIÇÃO PARA {nome_servico} ({nome_modelo})...", flush=True)

            resposta_llm = await llm_service.gerar_texto(
                prompt=mega_prompt, 
                modelo=nome_modelo,
                company_id=company_id, 
                group_id=group_ids
            )
            
            print(f"✅ RESPOSTA RECEBIDA DO LLM! (Tamanho: {len(resposta_llm)} chars)", flush=True)

            if resposta_llm and nome_arquivo_saida:
                file_bytes = resposta_llm.encode('utf-8')
                logger.log_info_negocio("salvando_blob", f"Salvando relatório final no Blob Storage.", job_id=job_id, company_id=company_id, project_id=project_id, extra={"filename": nome_arquivo_saida})
                
                caminho_blob = await self.blob_storage.save_document(
                    company_id=company_id,
                    project_id=project_id,
                    job_id=job_id,
                    file_data=file_bytes,
                    filename=nome_arquivo_saida,
                    group_id=group_ids
                )
                logger.log_info_negocio("blob_salvo", f"Relatório salvo em: {caminho_blob}", job_id=job_id, company_id=company_id, project_id=project_id)
                
            logger.log_saida_funcao("executar_analise", job_id=job_id, company_id=company_id, project_id=project_id, mensagem="Análise IA finalizada")
            return resposta_llm
            
        except Exception as e:
            logger.log_erro("erro_executar_analise", f"Erro ao executar análise: {e}", job_id=job_id, company_id=company_id, project_id=project_id)
            print(f"\n❌ ERRO CRÍTICO NA EXECUÇÃO DA IA: {str(e)}", flush=True)
            raise
