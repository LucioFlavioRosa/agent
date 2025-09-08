import os
import json
from datetime import datetime
from azure.data.tables import TableServiceClient, TableEntity
from typing import Dict, Any, Optional

class AzureTableLogger:
    def __init__(self):
        connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        if not connection_string:
            raise ValueError("AZURE_STORAGE_CONNECTION_STRING não encontrada nas variáveis de ambiente")
        
        self.table_service_client = TableServiceClient.from_connection_string(connection_string)
        self.table_name = "TokenUsageLogs"
        
        # Cria a tabela se não existir
        try:
            self.table_service_client.create_table_if_not_exists(table_name=self.table_name)
        except Exception as e:
            print(f"Erro ao criar/verificar tabela: {e}")

    def log_tokens(self, projeto: str, analysis_type: str, llm_model: str, 
                   tokens_in: int, tokens_out: int, data: Dict[str, Any], 
                   hora: str, status_update: str, job_id: str) -> bool:
        
        # [DEBUG] Log dos parâmetros recebidos
        print(f"[DEBUG] log_tokens recebeu: projeto={projeto}, analysis_type={analysis_type}, llm_model={llm_model}, tokens_in={tokens_in}, tokens_out={tokens_out}, hora={hora}, status_update={status_update}, job_id={job_id}")
        
        try:
            # Gera um ID único para a entidade
            entity_id = f"{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            
            entity = TableEntity()
            entity['PartitionKey'] = projeto
            entity['RowKey'] = entity_id
            entity['AnalysisType'] = analysis_type
            entity['LLMModel'] = llm_model
            entity['TokensIn'] = tokens_in
            entity['TokensOut'] = tokens_out
            entity['TotalTokens'] = tokens_in + tokens_out
            entity['Data'] = json.dumps(data, ensure_ascii=False)
            entity['Hora'] = hora
            entity['StatusUpdate'] = status_update
            entity['JobId'] = job_id
            entity['Timestamp'] = datetime.now()
            
            # Insere a entidade na tabela
            self.table_service_client.get_table_client(table_name=self.table_name).create_entity(entity=entity)
            
            print(f"[DEBUG] Token usage registrado com sucesso na Azure Table: {entity_id}")
            return True
            
        except Exception as e:
            print(f"Erro ao registrar token usage na Azure Table: {e}")
            return False

# Instância global para uso em outros módulos
azure_logger = AzureTableLogger()

def log_tokens(projeto: str, analysis_type: str, llm_model: str, 
               tokens_in: int, tokens_out: int, data: Dict[str, Any], 
               hora: str, status_update: str, job_id: str) -> bool:
    return azure_logger.log_tokens(projeto, analysis_type, llm_model, 
                                   tokens_in, tokens_out, data, 
                                   hora, status_update, job_id)