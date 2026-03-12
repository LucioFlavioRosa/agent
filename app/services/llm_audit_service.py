import logging
from datetime import datetime
from typing import Optional, Any, List
from azure.data.tables.aio import TableServiceClient
from azure.core.exceptions import ResourceExistsError

logger = logging.getLogger("mcp.llm_audit_service")

class LLMAuditService:
    def __init__(self, vault_service):
        """
        Serviço de auditoria conectando diretamente ao Azure Table Storage.
        Recebe o vault_service para puxar as credenciais.
        """
        self.vault_service = vault_service
        self.table_name = "LLMUsageMetrics" # Nome da Tabela na Azure

    def _normalize_group_id(self, group_id: Any) -> Optional[str]:
        if isinstance(group_id, list):
            return str(group_id[0]) if group_id else None
        return str(group_id) if group_id else None

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
        """Salva a interação do usuário como uma linha estruturada na Tabela Azure."""
        try:
            safe_group_id = self._normalize_group_id(group_ids)
            
            # 1. Pega a mesma Connection String usada para os Blobs
            conn_str = await self.vault_service.get_secret(
                base_name='blobstorage-connection-string', 
                company_id=company_id, 
                group_id=safe_group_id,
                vault_type='infra'
            )
            
            if not conn_str:
                logger.error("[AUDITORIA] Connection string não encontrada.")
                return False

            # 2. Conecta no serviço de Tabelas da Azure
            table_service_client = TableServiceClient.from_connection_string(conn_str=conn_str)
            
            async with table_service_client:
                # 3. Cria a tabela se não existir (só executa a criação na primeira vez)
                try:
                    await table_service_client.create_table(table_name=self.table_name)
                except ResourceExistsError:
                    pass # Se já existe, segue o jogo!
                    
                table_client = table_service_client.get_table_client(table_name=self.table_name)
                
                # 4. Estrutura da Linha (Entidade)
                # PartitionKey: Agrupa os dados. Agrupar por Empresa facilita consultar "Quanto a empresa X gastou?"
                # RowKey: Identificador único da linha no banco.
                entity = {
                    "PartitionKey": company_id,
                    "RowKey": f"{project_id}_{job_id}",
                    "TimestampUTC": datetime.utcnow().isoformat(),
                    "UserEmail": user_email,
                    "ProjectID": project_id,
                    "JobID": job_id,
                    "AgentType": analysis_type,
                    "ModelName": model_name,
                    "InputTokens": input_tokens,
                    "OutputTokens": output_tokens,
                    "TotalTokens": input_tokens + output_tokens,
                    "GroupIDs": str(group_ids)
                }

                # 5. Adiciona a linha na tabela
                await table_client.create_entity(entity=entity)
            
            print(f"✅ [AUDITORIA FINOPS] Métricas registradas na Tabela '{self.table_name}' (Tokens: {input_tokens + output_tokens}).", flush=True)
            return True
            
        except Exception as audit_err:
            print(f"⚠️ [AVISO - AUDITORIA] Falha ao salvar na Azure Table: {audit_err}", flush=True)
            logger.error(f"Erro no LLMAuditService: {audit_err}")
            return False
