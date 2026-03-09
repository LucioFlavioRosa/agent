import logging
import traceback
from typing import Optional
from app.config.agent_mapping import AGENT_CONFIG

logger = logging.getLogger("mcp_prototype.agent_service")

class AgentService:
    def __init__(self, context_retrieval_service, blob_storage_service, llm_services: dict):
        self.context_retrieval = context_retrieval_service
        self.blob_storage = blob_storage_service
        self.llm_services = llm_services # Contém o 'bedrock_service'

    async def executar_analise(self, task_payload: dict, texto_instrucoes: str, texto_identidade: str) -> str:
        """
        Orquestra a chamada para a IA e o salvamento do arquivo HTML final.
        """
        job_id = task_payload.get("job_id")
        company_id = task_payload.get("company_id")
        project_id = task_payload.get("project_id")
        group_id = task_payload.get("group_ids")
        analysis_type = task_payload.get("analysis_type", "agent_prototype_generator_digital")
        comentario_extra = task_payload.get("comentario_extra", "")

        try:
            print(f"🛠️ [AGENTE] Iniciando execução para Job {job_id}...", flush=True)

            # 1. Recupera o contexto (Épicos, Features, etc.)
            context_string = await self.context_retrieval.build_context_string(
                company_id=company_id,
                project_id=project_id,
                context_used=task_payload.get("context_used", {}),
                group_ids=group_id
            )

            # 2. Monta o Prompt (Simples para teste)
            prompt_final = f"""
            Você é um desenvolvedor Frontend experiente.
            Instruções do Usuário: {texto_instrucoes}
            Identidade Visual: {texto_identidade}
            Contexto do Projeto: {context_string}
            Comentário Extra: {comentario_extra}
            
            Gere um código HTML único, completo e funcional com Tailwind CSS. 
            Responda APENAS com o código HTML.
            """

            # 3. Chama o Bedrock (Passando os IDs para o Vault funcionar)
            bedrock = self.llm_services.get("bedrock_service")
            if not bedrock:
                raise ValueError("Serviço Bedrock não encontrado no registro.")

            print(f"📡 [AGENTE] Chamando Bedrock para empresa {company_id}...", flush=True)
            
            codigo_html = await bedrock.gerar_texto(
                prompt=prompt_final,
                company_id=company_id,
                job_id=job_id # O VaultService usará isso para achar as chaves AWS
            )

            # 4. Salva o resultado no Blob
            config = AGENT_CONFIG.get(analysis_type, {})
            filename = config.get("output_filename", "index.html")
            
            print(f"💾 [AGENTE] Salvando resultado em {filename}...", flush=True)
            
            await self.blob_storage.save_document(
                company_id=company_id,
                project_id=project_id,
                job_id=job_id,
                file_data=codigo_html.encode('utf-8'),
                filename=filename,
                group_id=group_id
            )

            return codigo_html

        except Exception as e:
            print(f"❌ [AGENTE] ERRO CRÍTICO: {str(e)}", flush=True)
            traceback.print_exc()
            raise
