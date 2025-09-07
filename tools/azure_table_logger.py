import os
import threading
from datetime import datetime
from azure.data.tables import TableServiceClient, TableEntity
from typing import Optional

class AzureTableLogger:
    def __init__(self):
        self.connection_string = os.environ.get("AZURE_TABLE_CONN_STRING")
        self.table_name = os.environ.get("AZURE_TABLE_NAME", "tokenlogs")
        self.table_service_client = None
        
        if self.connection_string:
            try:
                self.table_service_client = TableServiceClient.from_connection_string(
                    conn_str=self.connection_string
                )
                self.table_client = self.table_service_client.get_table_client(
                    table_name=self.table_name
                )
                self.table_client.create_table(exist_ok=True)
            except Exception as e:
                print(f"Erro ao inicializar Azure Table Logger: {e}")
                self.table_service_client = None
    
    def _log_tokens_sync(self, job_id: str, tokens_in: int, tokens_out: int, timestamp: str):
        if not self.table_service_client:
            print("Azure Table Logger não configurado. Log de tokens ignorado.")
            return
        
        try:
            entity = TableEntity()
            entity["PartitionKey"] = "tokens"
            entity["RowKey"] = job_id
            entity["JobId"] = job_id
            entity["TokensIn"] = tokens_in
            entity["TokensOut"] = tokens_out
            entity["Timestamp"] = timestamp
            entity["CreatedAt"] = datetime.utcnow().isoformat()
            
            self.table_client.create_entity(entity=entity)
            print(f"Log de tokens salvo com sucesso para job_id: {job_id}")
        except Exception as e:
            print(f"Erro ao salvar log de tokens: {e}")
    
    def log_tokens_async(self, job_id: str, tokens_in: int, tokens_out: int, timestamp: str):
        thread = threading.Thread(
            target=self._log_tokens_sync,
            args=(job_id, tokens_in, tokens_out, timestamp),
            daemon=True
        )
        thread.start()

_logger_instance = AzureTableLogger()

def log_tokens_async(job_id: str, tokens_in: int, tokens_out: int, timestamp: str):
    _logger_instance.log_tokens_async(job_id, tokens_in, tokens_out, timestamp)