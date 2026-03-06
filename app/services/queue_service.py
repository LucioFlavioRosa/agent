import io
import os
import docx
import json
import httpx
import base64
import asyncio
import logging
from typing import Optional
from azure.storage.queue.aio import QueueClient

from app.services.vault_service import vault_service
from app.services.blob_storage_service import blob_storage_service

# Importamos o serviço de LLM que criamos anteriormente
from app.services.llm_service import generate_html_prototype

logger = logging.getLogger("mcp_prototype.queue_service")

class QueueService:
    def __init__(self, queue_name: str, max_concurrent_workers: int = 5):
        self.vault_service = vault_service
        self.blob_storage_service = blob_storage_service
        self.queue_name = queue_name
        self.max_concurrent_workers = max_concurrent_workers
        self.internal_queue = asyncio.Queue(maxsize=max_concurrent_workers * 2)

    async def _notificar_backend(
        self, 
        job_id: str, 
        company_id: str, 
        project_id: str, 
        status: str,
        category: str,
        blob_path: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Envia o webhook avisando o Maestro que o Job acabou."""
        backend_base_url = os.getenv("BACKEND_WEBHOOK_URL", "http://host.docker.internal:8000").rstrip('/')
        webhook_url = f"{backend_base_url}/internal/jobs/{job_id}/complete"
        
        payload = {
            "project_id": project_id,
            "company_id": company_id,
            "status": status,
            "category": category,
            "blob_path": blob_path,
            "error_message": error_message
        }

        logger.info(f"webhook_iniciado | Chamando: POST {webhook_url} | Job: {job_id}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload, timeout=15.0)
                response.raise_for_status() 
                logger.info(f"webhook_sucesso | Backend atualizado para '{status}' | Job: {job_id}")
                
        except httpx.HTTPStatusError as exc:
            logger.error(f"webhook_erro_http | Backend rejeitou: {exc.response.status_code} | Job: {job_id}")
        except Exception as e:
            logger.error(f"webhook_erro_rede | Falha ao notificar: {str(e)} | Job: {job_id}")

    async def _extract_text_from_blob(self, company_id: str, blob_path: str, group_ids: list) -> str:
        """Função auxiliar para baixar o DOCX do Blob e extrair o texto"""
        if not blob_path: return ""
        try:
            file_bytes = await self.blob_storage_service.download_document(
                company_id=company_id, blob_path=blob_path, group_id=group_ids[0] if group_ids else None
            )
            doc = docx.Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        except Exception as e:
            logger.error(f"Erro ao ler DOCX do blob {blob_path}: {e}")
            return ""

    async def process_single_message(self, msg, queue_client: QueueClient, worker_id: int):
        try:
            decoded_str = base64.b64decode(msg.content).decode('utf-8')
            task_data = json.loads(decoded_str)
            
            job_id = task_data.get('job_id')
            company_id = task_data.get('company_id')
            project_id = task_data.get('project_id')
            group_ids = task_data.get('group_ids', [])
            analysis_type = task_data.get("analysis_type", "unknown")
            context_used = task_data.get("context_used", {})
            comentario_extra = task_data.get("comentario_extra", "")
            
            # Caminhos dos arquivos enviados pelo usuário e salvos pelo Maestro no Blob
            blob_instrucoes = task_data.get('blob_path') 
            blob_identidade = task_data.get('identidade_visual_blob_path')
            
            logger.info(f"job_recebido_fila | Job: {job_id} | Worker: {worker_id}")
            
            # 1. Extração dos textos das instruções enviadas pelo usuário
            texto_instrucoes = await self._extract_text_from_blob(company_id, blob_instrucoes, group_ids)
            texto_identidade = await self._extract_text_from_blob(company_id, blob_identidade, group_ids)

            # 2. Resgatar contexto histórico (Épicos, Features, e HTML Anterior) do Blob
            # Nota: O Maestro precisa enviar os caminhos (paths) no context_used
            texto_epico = ""
            if "epics_blob_path" in context_used:
                epics_bytes = await self.blob_storage_service.download_document(company_id, context_used["epics_blob_path"])
                texto_epico = epics_bytes.decode('utf-8') # Assumindo que o agente de epics salvou como texto/md
                
            texto_features = ""
            if "features_blob_path" in context_used:
                feat_bytes = await self.blob_storage_service.download_document(company_id, context_used["features_blob_path"])
                texto_features = feat_bytes.decode('utf-8')

            # 🚀 LÓGICA DE REFINAMENTO: Baixa o HTML anterior!
            texto_prototipo_base = ""
            is_reviewer = "reviwer" in analysis_type.lower()
            if is_reviewer and "prototype_blob_path" in context_used:
                proto_bytes = await self.blob_storage_service.download_document(company_id, context_used["prototype_blob_path"])
                texto_prototipo_base = proto_bytes.decode('utf-8')

            # 3. Montar o Mega Prompt
            mega_prompt = f"Crie um protótipo HTML/CSS/JS (Single File).\n[ÉPICOS]\n{texto_epico}\n[FEATURES]\n{texto_features}"
            if is_reviewer and texto_prototipo_base:
                mega_prompt += f"\n[PROTÓTIPO ANTERIOR (REFINAR)]\n{texto_prototipo_base}"
            if texto_identidade:
                mega_prompt += f"\n[IDENTIDADE VISUAL]\n{texto_identidade}"
            if texto_instrucoes:
                mega_prompt += f"\n[INSTRUÇÕES GERAIS]\n{texto_instrucoes}"
            if comentario_extra:
                mega_prompt += f"\n[PROMPT DO USUÁRIO]\n{comentario_extra}"

            # 4. Chamar a IA para gerar o HTML
            logger.info(f"job_gerando_ia | Enviando para o LLM | Job: {job_id}")
            # Pegamos a chave do cofre para passar ao LLM
            api_key = await self.vault_service.get_secret("openai-api-key", company_id, vault_type="llm")
            html_gerado = await generate_html_prototype(mega_prompt, api_key)

            # 5. 🚀 SALVAR O ARQUIVO HTML GERADO NO BLOB STORAGE 🚀
            nome_arquivo_saida = "prototype.html" # A extensão mudou para HTML!
            caminho_salvo = await self.blob_storage_service.save_document(
                company_id=company_id,
                project_id=project_id,
                job_id=job_id,
                file_data=html_gerado.encode('utf-8'), # Salva como bytes
                filename=nome_arquivo_saida,
                group_id=group_ids[0] if group_ids else None
            )

            # Apaga a mensagem da fila pois deu sucesso
            await queue_client.delete_message(msg)

            # 6. Notifica o Backend Maestro
            await self._notificar_backend(
                job_id=job_id,
                company_id=company_id,
                project_id=project_id,
                status="done",
                category="prototype", # Categoria fixa e limpa
                blob_path=caminho_salvo # Envia o caminho do HTML recém salvo
            )
            
            logger.info(f"job_finalizado | Job: {job_id} | Salvo em: {caminho_salvo}")
            
        except Exception as e:
            logger.error(f"erro_processamento_job | Worker: {worker_id} | Erro: {e}")
            try:
                task_data = json.loads(base64.b64decode(msg.content).decode('utf-8'))
                await self._notificar_backend(
                    job_id=task_data.get("job_id"),
                    company_id=task_data.get("company_id"),
                    project_id=task_data.get("project_id"),
                    status="error",
                    category="prototype",
                    error_message=str(e)
                )
            except Exception:
                pass

    # ... (Os métodos _consumer_loop, start_worker e send_message continuam rigorosamente IGUAIS ao seu código original) ...
