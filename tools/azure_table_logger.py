import os
from datetime import datetime
from azure.data.tables import TableServiceClient, TableEntity
from typing import Optional
from tools.azure_secret_manager import AzureSecretManager

class AzureTableLogger:
    def __init__(self):
        print("[AzureTableLogger] Iniciando configuração do logger...")
        self.table_name = os.getenv("AZURE_TABLE_NAME", "tokenlogs")
        print(f"[AzureTableLogger] Nome da tabela: {self.table_name}")
        
        self.table_service_client = None
        self.secret_manager = AzureSecretManager()
        
        connection_string = None
        secret_name = os.getenv("AZURE_TABLE_CONN_STRING")
        print(f"[AzureTableLogger] Secret name da variável de ambiente: {secret_name}")
        
        if secret_name:
            try:
                print(f"[AzureTableLogger] Tentando obter connection string do Key Vault...")
                connection_string = self.secret_manager.get_secret(secret_name)
                print(f"[AzureTableLogger] Connection string obtida do Key Vault com sucesso (tamanho: {len(connection_string) if connection_string else 0})")
            except Exception as e:
                print(f"Warning: Failed to get connection string from Key Vault: {e}")
                connection_string = os.getenv("AZURE_TABLE_CONN_STRING")
                print(f"[AzureTableLogger] Usando connection string da variável de ambiente como fallback (tamanho: {len(connection_string) if connection_string else 0})")
        else:
            connection_string = os.getenv("AZURE_TABLE_CONN_STRING")
            print(f"[AzureTableLogger] Usando connection string diretamente da variável de ambiente (tamanho: {len(connection_string) if connection_string else 0})")
        
        if not connection_string:
            print(f"[AzureTableLogger] ERRO CRÍTICO: Connection string está vazia ou None")
            self.table_service_client = None
            return
        
        if connection_string:
            try:
                print(f"[AzureTableLogger] Criando TableServiceClient...")
                self.table_service_client = TableServiceClient.from_connection_string(
                    conn_str=connection_string
                )
                print(f"[AzureTableLogger] TableServiceClient criado com sucesso")
                
                print(f"[AzureTableLogger] Obtendo table client para tabela: {self.table_name}")
                self.table_client = self.table_service_client.get_table_client(
                    table_name=self.table_name
                )
                print(f"[AzureTableLogger] Table client obtido com sucesso")
                
                print(f"[AzureTableLogger] Criando tabela se não existir...")
                self.table_client.create_table(exist_ok=True)
                print(f"[AzureTableLogger] Tabela criada/verificada com sucesso")
            except Exception as e:
                print(f"Erro ao inicializar Azure Table Logger: {e}")
                print(f"[AzureTableLogger] Detalhes do erro de inicialização: {type(e).__name__}: {str(e)}")
                self.table_service_client = None
    
    @staticmethod
    def diagnostico_conexao():
        """Método de diagnóstico para verificar configurações e conexão"""
        diagnostico = {
            "azure_table_name": os.getenv("AZURE_TABLE_NAME"),
            "azure_table_conn_string_env_exists": bool(os.getenv("AZURE_TABLE_CONN_STRING")),
            "azure_table_conn_string_length": len(os.getenv("AZURE_TABLE_CONN_STRING", "")),
            "secret_manager_available": True,
            "connection_status": "unknown"
        }
        
        try:
            secret_manager = AzureSecretManager()
            secret_name = os.getenv("AZURE_TABLE_CONN_STRING")
            if secret_name:
                connection_string = secret_manager.get_secret(secret_name)
                diagnostico["secret_retrieval_success"] = bool(connection_string)
                diagnostico["secret_connection_string_length"] = len(connection_string) if connection_string else 0
            else:
                diagnostico["secret_retrieval_success"] = False
                diagnostico["secret_connection_string_length"] = 0
        except Exception as e:
            diagnostico["secret_manager_error"] = str(e)
            diagnostico["secret_retrieval_success"] = False
        
        try:
            logger_test = AzureTableLogger()
            diagnostico["connection_status"] = "success" if logger_test.table_service_client else "failed"
        except Exception as e:
            diagnostico["connection_status"] = f"error: {str(e)}"
        
        return diagnostico
    
    def log_tokens(self, projeto: str, analysis_type: str, llm_model: str, tokens_in: int, tokens_out: int, data: str, hora: str, status_update: str, job_id: str) -> bool:
        print(f"[AzureTableLogger] Iniciando log_tokens para job_id: {job_id}")
        print(f"[AzureTableLogger] Parâmetros recebidos:")
        print(f"[AzureTableLogger] - projeto: {projeto} (tipo: {type(projeto)})")
        print(f"[AzureTableLogger] - analysis_type: {analysis_type} (tipo: {type(analysis_type)})")
        print(f"[AzureTableLogger] - llm_model: {llm_model} (tipo: {type(llm_model)})")
        print(f"[AzureTableLogger] - tokens_in: {tokens_in} (tipo: {type(tokens_in)})")
        print(f"[AzureTableLogger] - tokens_out: {tokens_out} (tipo: {type(tokens_out)})")
        print(f"[AzureTableLogger] - data: {data} (tipo: {type(data)})")
        print(f"[AzureTableLogger] - hora: {hora} (tipo: {type(hora)})")
        print(f"[AzureTableLogger] - status_update: {status_update} (tipo: {type(status_update)})")
        print(f"[AzureTableLogger] - job_id: {job_id} (tipo: {type(job_id)})")
        
        # Validação de parâmetros
        if not projeto or not isinstance(projeto, str):
            print(f"[AzureTableLogger] ERRO: Parâmetro 'projeto' inválido: {projeto}")
            return False
        
        if not analysis_type or not isinstance(analysis_type, str):
            print(f"[AzureTableLogger] ERRO: Parâmetro 'analysis_type' inválido: {analysis_type}")
            return False
        
        if not llm_model or not isinstance(llm_model, str):
            print(f"[AzureTableLogger] ERRO: Parâmetro 'llm_model' inválido: {llm_model}")
            return False
        
        if not isinstance(tokens_in, int) or tokens_in < 0:
            print(f"[AzureTableLogger] ERRO: Parâmetro 'tokens_in' inválido: {tokens_in}")
            return False
        
        if not isinstance(tokens_out, int) or tokens_out < 0:
            print(f"[AzureTableLogger] ERRO: Parâmetro 'tokens_out' inválido: {tokens_out}")
            return False
        
        if not job_id or not isinstance(job_id, str):
            print(f"[AzureTableLogger] ERRO: Parâmetro 'job_id' inválido: {job_id}")
            return False
        
        if not self.table_service_client:
            print("Azure Table Logger não configurado. Log de tokens ignorado.")
            print(f"[AzureTableLogger] table_service_client é None - conexão não foi estabelecida")
            return False
        
        print(f"[AzureTableLogger] Validação de parâmetros concluída com sucesso")
        
        try:
            timestamp = datetime.utcnow().isoformat()
            row_key = f"{job_id}_{timestamp.replace(':', '-').replace('.', '-')}"
            print(f"[AzureTableLogger] Timestamp gerado: {timestamp}")
            print(f"[AzureTableLogger] RowKey gerado: {row_key}")
            
            print(f"[AzureTableLogger] Criando entidade TableEntity...")
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
            
            print(f"[AzureTableLogger] Entidade criada com sucesso:")
            print(f"[AzureTableLogger] - PartitionKey: {entity['PartitionKey']}")
            print(f"[AzureTableLogger] - RowKey: {entity['RowKey']}")
            print(f"[AzureTableLogger] - Projeto: {entity['Projeto']}")
            print(f"[AzureTableLogger] - JobId: {entity['JobId']}")
            
            print(f"[AzureTableLogger] Tentando inserir entidade na tabela...")
            self.table_client.create_entity(entity=entity)
            print(f"Log de tokens salvo com sucesso para job_id: {job_id}")
            print(f"[AzureTableLogger] Inserção na tabela concluída com sucesso")
            return True
            
        except Exception as e:
            print(f"AVISO: Falha no logging de tokens (não afeta o resultado principal): {e}")
            print(f"[AzureTableLogger] ERRO DETALHADO na inserção:")
            print(f"[AzureTableLogger] - Tipo do erro: {type(e).__name__}")
            print(f"[AzureTableLogger] - Mensagem do erro: {str(e)}")
            print(f"[AzureTableLogger] - Dados da entidade que causou erro:")
            try:
                print(f"[AzureTableLogger]   - PartitionKey: {projeto}")
                print(f"[AzureTableLogger]   - RowKey: {row_key}")
                print(f"[AzureTableLogger]   - JobId: {job_id}")
                print(f"[AzureTableLogger]   - Timestamp: {timestamp}")
                print(f"Detalhes do erro de logging - job_id: {job_id}, projeto: {projeto}, modelo: {llm_model}")
            except Exception as inner_e:
                print(f"Erro adicional ao tentar logar detalhes da falha: {inner_e}")
                print(f"[AzureTableLogger] Erro adicional (inner): {type(inner_e).__name__}: {str(inner_e)}")
            
            # Log adicional do estado do cliente
            print(f"[AzureTableLogger] Estado do cliente:")
            print(f"[AzureTableLogger] - table_service_client: {type(self.table_service_client) if self.table_service_client else 'None'}")
            print(f"[AzureTableLogger] - table_client: {type(self.table_client) if hasattr(self, 'table_client') and self.table_client else 'None'}")
            print(f"[AzureTableLogger] - table_name: {self.table_name}")
            
            return False

_logger_instance = AzureTableLogger()

def log_tokens(projeto: str, analysis_type: str, llm_model: str, tokens_in: int, tokens_out: int, data: str, hora: str, status_update: str, job_id: str) -> bool:
    print(f"[log_tokens] Função global chamada para job_id: {job_id}")
    try:
        return _logger_instance.log_tokens(projeto, analysis_type, llm_model, tokens_in, tokens_out, data, hora, status_update, job_id)
    except Exception as e:
        print(f"AVISO: Falha na função global de logging (não afeta o resultado principal): {e}")
        print(f"[log_tokens] ERRO na função global: {type(e).__name__}: {str(e)}")
        return False