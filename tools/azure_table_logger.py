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
        self.table_client = None
        self.secret_manager = AzureSecretManager()
        
        connection_string = None
        secret_name = os.getenv("AZURE_TABLE_CONN_STRING")
        print(f"[AzureTableLogger] Valor da variável AZURE_TABLE_CONN_STRING: {secret_name}")
        print(f"[AzureTableLogger] Tipo do valor: {type(secret_name)}")
        print(f"[AzureTableLogger] Tamanho do valor: {len(secret_name) if secret_name else 0}")
        
        if secret_name:
            if self._is_connection_string(secret_name):
                print(f"[AzureTableLogger] Valor parece ser uma connection string direta (tamanho: {len(secret_name)})")
                connection_string = secret_name
            else:
                print(f"[AzureTableLogger] Valor parece ser um nome de secret, tentando obter do Key Vault...")
                try:
                    connection_string = self.secret_manager.get_secret(secret_name)
                    if connection_string:
                        print(f"[AzureTableLogger] Connection string obtida do Key Vault com sucesso (tamanho: {len(connection_string)})")
                        print(f"[AzureTableLogger] Connection string é válida: {self._is_connection_string(connection_string)}")
                    else:
                        print(f"[AzureTableLogger] Key Vault retornou valor vazio ou None")
                except Exception as e:
                    print(f"[AzureTableLogger] ERRO ao obter secret do Key Vault: {type(e).__name__}: {str(e)}")
                    print(f"[AzureTableLogger] Tentando usar valor como connection string direta (fallback)")
                    connection_string = secret_name
        else:
            print(f"[AzureTableLogger] AZURE_TABLE_CONN_STRING não definida ou vazia")
        
        if not connection_string:
            print(f"[AzureTableLogger] ERRO CRÍTICO: Connection string está vazia ou None após todas as tentativas")
            self.table_service_client = None
            return
        
        if not self._is_connection_string(connection_string):
            print(f"[AzureTableLogger] AVISO: Connection string não parece ter formato válido")
            print(f"[AzureTableLogger] Primeiros 50 caracteres: {connection_string[:50]}...")
        
        try:
            print(f"[AzureTableLogger] Criando TableServiceClient com connection string (tamanho: {len(connection_string)})...")
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
            
            print(f"[AzureTableLogger] Inicialização concluída com SUCESSO")
        except Exception as e:
            print(f"[AzureTableLogger] ERRO CRÍTICO na inicialização: {type(e).__name__}: {str(e)}")
            print(f"[AzureTableLogger] Connection string usada (primeiros 50 chars): {connection_string[:50] if connection_string else 'None'}...")
            self.table_service_client = None
            self.table_client = None
    
    def _is_connection_string(self, value: str) -> bool:
        if not value or not isinstance(value, str):
            return False
        return value.strip().startswith("DefaultEndpointsProtocol=")
    
    def test_connection(self) -> dict:
        result = {
            "connection_established": False,
            "table_client_available": False,
            "table_exists": False,
            "can_insert": False,
            "error": None
        }
        
        try:
            if not self.table_service_client:
                result["error"] = "TableServiceClient não foi inicializado"
                return result
            
            result["connection_established"] = True
            
            if not self.table_client:
                result["error"] = "TableClient não foi inicializado"
                return result
            
            result["table_client_available"] = True
            
            try:
                tables = list(self.table_service_client.list_tables())
                table_names = [table.name for table in tables]
                result["table_exists"] = self.table_name in table_names
                print(f"[AzureTableLogger] Tabelas disponíveis: {table_names}")
            except Exception as e:
                result["error"] = f"Erro ao listar tabelas: {str(e)}"
                return result
            
            try:
                test_entity = TableEntity(
                    PartitionKey="TEST",
                    RowKey=f"test_{datetime.utcnow().isoformat().replace(':', '-').replace('.', '-')}",
                    TestField="connection_test",
                    CreatedAt=datetime.utcnow().isoformat()
                )
                self.table_client.create_entity(entity=test_entity)
                result["can_insert"] = True
                print(f"[AzureTableLogger] Teste de inserção bem-sucedido")
                
                try:
                    self.table_client.delete_entity(
                        partition_key=test_entity["PartitionKey"],
                        row_key=test_entity["RowKey"]
                    )
                    print(f"[AzureTableLogger] Entidade de teste removida com sucesso")
                except:
                    print(f"[AzureTableLogger] Não foi possível remover entidade de teste (não crítico)")
                    
            except Exception as e:
                result["error"] = f"Erro ao testar inserção: {str(e)}"
                return result
                
        except Exception as e:
            result["error"] = f"Erro geral no teste de conexão: {str(e)}"
        
        return result
    
    @staticmethod
    def diagnostico_conexao():
        diagnostico = {
            "azure_table_name": os.getenv("AZURE_TABLE_NAME"),
            "azure_table_conn_string_env_exists": bool(os.getenv("AZURE_TABLE_CONN_STRING")),
            "azure_table_conn_string_length": len(os.getenv("AZURE_TABLE_CONN_STRING", "")),
            "azure_table_conn_string_is_connection_string": False,
            "secret_manager_available": True,
            "connection_status": "unknown",
            "test_connection_result": None
        }
        
        env_value = os.getenv("AZURE_TABLE_CONN_STRING", "")
        if env_value:
            diagnostico["azure_table_conn_string_is_connection_string"] = env_value.strip().startswith("DefaultEndpointsProtocol=")
        
        try:
            secret_manager = AzureSecretManager()
            secret_name = os.getenv("AZURE_TABLE_CONN_STRING")
            if secret_name and not diagnostico["azure_table_conn_string_is_connection_string"]:
                connection_string = secret_manager.get_secret(secret_name)
                diagnostico["secret_retrieval_success"] = bool(connection_string)
                diagnostico["secret_connection_string_length"] = len(connection_string) if connection_string else 0
                diagnostico["secret_is_valid_connection_string"] = connection_string and connection_string.strip().startswith("DefaultEndpointsProtocol=") if connection_string else False
            else:
                diagnostico["secret_retrieval_success"] = False
                diagnostico["secret_connection_string_length"] = 0
                diagnostico["secret_is_valid_connection_string"] = False
        except Exception as e:
            diagnostico["secret_manager_error"] = str(e)
            diagnostico["secret_retrieval_success"] = False
        
        try:
            logger_test = AzureTableLogger()
            diagnostico["connection_status"] = "success" if logger_test.table_service_client else "failed"
            
            if logger_test.table_service_client:
                test_result = logger_test.test_connection()
                diagnostico["test_connection_result"] = test_result
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
            print("[AzureTableLogger] ERRO: Azure Table Logger não configurado. Log de tokens ignorado.")
            print(f"[AzureTableLogger] table_service_client é None - conexão não foi estabelecida")
            print(f"[AzureTableLogger] Execute diagnostico_conexao() para mais detalhes")
            return False
        
        if not self.table_client:
            print("[AzureTableLogger] ERRO: Table client não disponível")
            return False
        
        print(f"[AzureTableLogger] Validação de parâmetros concluída com sucesso")
        
        try:
            timestamp = datetime.utcnow().isoformat()
            row_key = f"{job_id}_{timestamp.replace(':', '-').replace('.', '-')}"
            print(f"[AzureTableLogger] Timestamp gerado: {timestamp}")
            print(f"[AzureTableLogger] RowKey gerado: {row_key}")
            
            print(f"[AzureTableLogger] Criando entidade TableEntity...")
            entity = TableEntity(
                PartitionKey=projeto,
                RowKey=row_key,
                Projeto=projeto,
                AnalysisType=analysis_type,
                LLMModel=llm_model,
                TokensIn=tokens_in,
                TokensOut=tokens_out,
                Data=data,
                Hora=hora,
                StatusUpdate=status_update,
                JobId=job_id,
                CreatedAt=timestamp
            )
            
            print(f"[AzureTableLogger] Entidade criada com sucesso:")
            print(f"[AzureTableLogger] - PartitionKey: {entity['PartitionKey']}")
            print(f"[AzureTableLogger] - RowKey: {entity['RowKey']}")
            print(f"[AzureTableLogger] - Projeto: {entity['Projeto']}")
            print(f"[AzureTableLogger] - JobId: {entity['JobId']}")
            
            print(f"[AzureTableLogger] Tentando inserir entidade na tabela...")
            self.table_client.create_entity(entity=entity)
            print(f"[AzureTableLogger] Log de tokens salvo com sucesso para job_id: {job_id}")
            print(f"[AzureTableLogger] Inserção na tabela concluída com sucesso")
            return True
            
        except Exception as e:
            print(f"[AzureTableLogger] AVISO: Falha no logging de tokens (não afeta o resultado principal): {e}")
            print(f"[AzureTableLogger] ERRO DETALHADO na inserção:")
            print(f"[AzureTableLogger] - Tipo do erro: {type(e).__name__}")
            print(f"[AzureTableLogger] - Mensagem do erro: {str(e)}")
            print(f"[AzureTableLogger] - Dados da entidade que causou erro:")
            try:
                print(f"[AzureTableLogger]   - PartitionKey: {projeto}")
                print(f"[AzureTableLogger]   - RowKey: {row_key}")
                print(f"[AzureTableLogger]   - JobId: {job_id}")
                print(f"[AzureTableLogger]   - Timestamp: {timestamp}")
                print(f"[AzureTableLogger] Detalhes do erro de logging - job_id: {job_id}, projeto: {projeto}, modelo: {llm_model}")
            except Exception as inner_e:
                print(f"[AzureTableLogger] Erro adicional ao tentar logar detalhes da falha: {inner_e}")
                print(f"[AzureTableLogger] Erro adicional (inner): {type(inner_e).__name__}: {str(inner_e)}")
            
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
        print(f"[log_tokens] AVISO: Falha na função global de logging (não afeta o resultado principal): {e}")
        print(f"[log_tokens] ERRO na função global: {type(e).__name__}: {str(e)}")
        return False