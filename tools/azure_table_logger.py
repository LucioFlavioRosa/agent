import os
import threading
from datetime import datetime
from azure.data.tables import TableServiceClient, TableEntity
from typing import Optional
from tools.azure_secret_manager import AzureSecretManager

class AzureTableLogger:
    def __init__(self):
        self.table_name = os.getenv("AZURE_TABLE_NAME", "tokenlogs")
        self.table_service_client = None
        self.secret_manager = AzureSecretManager()
        
        connection_string = None
        secret_name = os.getenv("AZURE_TABLE_CONN_STRING")
        
        if secret_name:
            try:
                connection_string = self.secret_manager.get_secret(secret_name)
            except Exception as e:
                print(f"Warning: Failed to get connection string from Key Vault: {e}")
                connection_string = os.getenv("AZURE_TABLE_CONN_STRING")
        else:
            connection_string = os.getenv("AZURE_TABLE_CONN_STRING")
        
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
            
            entity = TableEntity(
            PartitionKey = projeto,
            RowKey = row_key,
            Projeto = projeto,
            AnalysisType = analysis_type,
            LLMModel = llm_model,
            TokensIn = tokens_in,
            TokensOut = tokens_out,
            Data = data,
            Hora = hora,
            StatusUpdate = status_update,
            JobId = job_id,
            CreatedAt = timestamp
            )
            
            self.table_client.create_entity(entity=entity)
            print(f"Log de tokens salvo com sucesso para job_id: {job_id}")
        except Exception as e:
            print(f"AVISO: Falha no logging de tokens (não afeta o resultado principal): {e}")
            try:
                print(f"Detalhes do erro de logging - job_id: {job_id}, projeto: {projeto}, modelo: {llm_model}")
            except Exception:
                print("Erro adicional ao tentar logar detalhes da falha")
    
    def log_tokens_async(self, projeto: str, analysis_type: str, llm_model: str, tokens_in: int, tokens_out: int, data: str, hora: str, status_update: str, job_id: str):
        try:
            thread = threading.Thread(
                target=self._log_tokens_sync,
                args=(projeto, analysis_type, llm_model, tokens_in, tokens_out, data, hora, status_update, job_id),
                daemon=True
            )
            thread.start()
        except Exception as e:
            print(f"AVISO: Falha ao iniciar thread de logging assíncrono (não afeta o resultado principal): {e}")

_logger_instance = AzureTableLogger()

def log_tokens_async(projeto: str, analysis_type: str, llm_model: str, tokens_in: int, tokens_out: int, data: str, hora: str, status_update: str, job_id: str):
    try:
        _logger_instance.log_tokens_async(projeto, analysis_type, llm_model, tokens_in, tokens_out, data, hora, status_update, job_id)
    except Exception as e:
        print(f"AVISO: Falha na função global de logging assíncrono (não afeta o resultado principal): {e}")
