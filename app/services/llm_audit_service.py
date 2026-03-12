import json
import logging
from datetime import datetime
from typing import Optional, Any

from app.services.blob_storage_service import BlobStorageService

logger = logging.getLogger("mcp_prototype.llm_audit_service")

class LLMAuditService:
    def __init__(self, blob_storage_service: BlobStorageService):
        """
        Serviço dedicado para auditoria e FinOps (controle de custos LLM).
        Reaproveita o blob_storage_service já instanciado no sistema.
        """
        self.blob_storage = blob_storage_service

    async def save_usage_metrics(
        self,
        company_id: str,
        project_id: str,
        job_id: str,
        user_email: str,
        analysis_type: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        group_ids: Optional[Any] = None
    ) -> bool:
        """
        Monta o registro de uso de tokens e salva como JSON no Blob Storage.
        """
        try:
            audit_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "user_email": user_email,
                "company_id": company_id,
                "group_ids": group_ids,
                "project_id": project_id,
                "job_id": job_id,
                "agent_type": analysis_type,
                "model_name": model_name,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            }

            # Converte o registro para bytes no formato JSON
            audit_bytes = json.dumps(audit_record, indent=4).encode('utf-8')

            # Salva o arquivo de auditoria na mesma pasta do Job no Blob Storage
            await self.blob_storage.save_document(
                company_id=company_id,
                project_id=project_id,
                job_id=job_id,
                file_data=audit_bytes,
                filename="llm_usage_metrics.json",
                group_id=group_ids
            )
            
            print(f"✅ [AUDITORIA] Métricas salvadas via LLMAuditService (Tokens: {input_tokens + output_tokens}).", flush=True)
            return True
            
        except Exception as audit_err:
            # Logamos o erro, mas retornamos False em vez de quebrar (Crash) a aplicação
            print(f"⚠️ [AVISO - AUDITORIA] Falha ao salvar a auditoria no Blob: {audit_err}", flush=True)
            logger.error(f"Erro no LLMAuditService: {audit_err}")
            return False
