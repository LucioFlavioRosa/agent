import os
import uuid
from datetime import datetime
from azure.data.tables import TableServiceClient, TableEntity
from typing import Optional

def log_tokens(projeto: str, tipo_tarefa: str, modelo: str, tokens_entrada: int, 
               tokens_saida: int, duracao_segundos: float, job_id: str) -> None:
    
    print(f"[DEBUG] log_tokens recebidos:")
    print(f"  - projeto: {projeto}")
    print(f"  - tipo_tarefa: {tipo_tarefa}")
    print(f"  - modelo: {modelo}")
    print(f"  - tokens_entrada: {tokens_entrada}")
    print(f"  - tokens_saida: {tokens_saida}")
    print(f"  - duracao_segundos: {duracao_segundos}")
    print(f"  - job_id: {job_id}")
    
    try:
        connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        if not connection_string:
            print(f"[ERRO] AZURE_STORAGE_CONNECTION_STRING não configurada")
            return
        
        table_name = "TokenUsage"
        
        table_service_client = TableServiceClient.from_connection_string(conn_str=connection_string)
        table_client = table_service_client.get_table_client(table_name=table_name)
        
        entity_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        
        entity = TableEntity()
        entity['PartitionKey'] = projeto
        entity['RowKey'] = entity_id
        entity['TipoTarefa'] = tipo_tarefa
        entity['Modelo'] = modelo
        entity['TokensEntrada'] = tokens_entrada
        entity['TokensSaida'] = tokens_saida
        entity['DuracaoSegundos'] = duracao_segundos
        entity['JobId'] = job_id
        entity['Timestamp'] = timestamp
        
        print(f"[DEBUG] Entidade preparada para inserção: {entity}")
        
        table_client.create_entity(entity=entity)
        
        print(f"[DEBUG] Token usage registrado com sucesso na Azure Table - ID: {entity_id}")
        
    except Exception as e:
        print(f"[ERRO] Falha ao registrar token usage na Azure Table: {e}")
        raise