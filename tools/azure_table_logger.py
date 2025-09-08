import os
import threading
from datetime import datetime
from azure.data.tables import TableServiceClient, TableEntity
from typing import Optional
from tools.azure_secret_manager import AzureSecretManager

class AzureTableLogger:
    def __init__(self):
        self.table_name = os.environ.get("AZURE_TABLE_NAME", "tokenlogs")
        self.table_service_client = None
        self.secret_manager = AzureSecretManager()
        
        connection_string = None
        secret_name = os.environ.get("AZURE_TABLE_CONN_STRING")
        
        if secret_name:
            try:
                connection_string = self.secret_manager.get_secret(secret_name)
            except Exception as e:
                print(f"Warning: Failed to get connection string from Key Vault: {e}")
                connection_string = os.environ.get("AZURE_TABLE_CONN_STRING")
        else:
            connection_string = os.environ.get("AZURE_TABLE_CONN_STRING")
        
        if connection_string:
            try:
                self.table_service_client = TableServiceClient.from_connection_string(
                    conn_str=connection_string
                )
                self.table_client = self.table_service_client.get_table_client(
                    table_name=self.table_name
                )
                self.table_client.create_table(exist_ok=True)
            except Exception as e:
                print(f"Erro ao inicializar Azure Table Logger: {e}")
                self.table_service_client = None
    
    def _log_tokens_sync(self, projeto: str, analysis_type: str, llm_model: str, tokens_in: int, tokens_out: int, data: str, hora: str, status_update: str, job_id: str):
        if not self.table_service_client:
            print("Azure Table Logger não configurado. Log de tokens ignorado.")
            return
        
        try:
            timestamp = datetime.utcnow().isoformat()
            row_key = f"{job_id}_{timestamp.replace(':', '-').replace('.', '-')}"
            
            entity = TableEntity()
            entity["PartitionKey"] = projeto
            entity["RowKey"] = row_key
            entity["Projeto"] = projeto
            entity["AnalysisType"] = analysis_type
            entity["LLMModel"] = llm_model
            entity["TokensIn"] = tokens_in
            entity["TokensOut"] = tokens_out
            entity["Data"] = data
            entity["Hora"] = hora
            entity["StatusUpdate"] = status_update
            entity["JobId"] = job_id
            entity["CreatedAt"] = timestamp
            
            self.table_client.create_entity(entity=entity)
            print(f"Log de tokens salvo com sucesso para job_id: {job_id}")
        except Exception as e:
            print(f"Erro ao salvar log de tokens: {e}")
    
    def log_tokens_async(self, projeto: str, analysis_type: str, llm_model: str, tokens_in: int, tokens_out: int, data: str, hora: str, status_update: str, job_id: str):
        thread = threading.Thread(
            target=self._log_tokens_sync,
            args=(projeto, analysis_type, llm_model, tokens_in, tokens_out, data, hora, status_update, job_id),
            daemon=True
        )
        thread.start()

_logger_instance = AzureTableLogger()

def log_tokens_async(projeto: str, analysis_type: str, llm_model: str, tokens_in: int, tokens_out: int, data: str, hora: str, status_update: str, job_id: str):
    _logger_instance.log_tokens_async(projeto, analysis_type, llm_model, tokens_in, tokens_out, data, hora, status_update, job_id)