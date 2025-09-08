import json
import time
from typing import Dict, Any, Optional, List
from domain.interfaces.llm_provider_interface import ILLMProvider
from tools.readers.reader_geral import ReaderGeral
from tools.azure_table_logger import log_tokens

class AgenteRevisor:
    def __init__(self, repository_reader: ReaderGeral, llm_provider: ILLMProvider):
        self.repository_reader = repository_reader
        self.llm_provider = llm_provider
    
    def validate_logging_fields(self, projeto: str, tipo_tarefa: str, modelo_final: str, 
                               tokens_entrada: int, tokens_saida: int, job_id_final: str) -> bool:
        campos_obrigatorios = {
            'projeto': projeto,
            'tipo_tarefa': tipo_tarefa,
            'modelo_final': modelo_final,
            'tokens_entrada': tokens_entrada,
            'tokens_saida': tokens_saida,
            'job_id_final': job_id_final
        }
        
        for nome_campo, valor in campos_obrigatorios.items():
            if valor is None or (isinstance(valor, str) and not valor.strip()):
                print(f"[ERRO] Campo obrigatório '{nome_campo}' está nulo ou vazio: {valor}")
                return False
            if nome_campo in ['tokens_entrada', 'tokens_saida'] and not isinstance(valor, int):
                print(f"[ERRO] Campo '{nome_campo}' deve ser um inteiro: {valor} (tipo: {type(valor)})")
                return False
        
        print(f"[DEBUG] Validação de campos concluída com sucesso")
        return True
    
    def main(self, repositorio: str, nome_branch: Optional[str], instrucoes_extras: Optional[str],
             usar_rag: bool = False, model_name: Optional[str] = None, 
             arquivos_especificos: Optional[List[str]] = None, repository_type: str = 'github',
             job_id: Optional[str] = None, projeto: Optional[str] = None, 
             llm_model: Optional[str] = None, status_update: Optional[str] = None) -> Dict[str, Any]:
        
        print(f"[DEBUG] Dados recebidos no AgenteRevisor:")
        print(f"  - repositorio: {repositorio}")
        print(f"  - nome_branch: {nome_branch}")
        print(f"  - instrucoes_extras: {instrucoes_extras[:100] if instrucoes_extras else None}...")
        print(f"  - usar_rag: {usar_rag}")
        print(f"  - model_name: {model_name}")
        print(f"  - arquivos_especificos: {arquivos_especificos}")
        print(f"  - repository_type: {repository_type}")
        print(f"  - job_id: {job_id}")
        print(f"  - projeto: {projeto}")
        print(f"  - llm_model: {llm_model}")
        print(f"  - status_update: {status_update}")
        
        start_time = time.time()
        
        try:
            arquivos_lidos = self.repository_reader.ler_repositorio(
                repositorio=repositorio,
                nome_branch=nome_branch,
                arquivos_especificos=arquivos_especificos,
                repository_type=repository_type
            )
            
            contexto_completo = {
                "arquivos_do_repositorio": arquivos_lidos,
                "instrucoes_extras": instrucoes_extras or "",
                "usar_rag": usar_rag
            }
            
            resposta_llm = self.llm_provider.processar_requisicao(
                contexto=contexto_completo,
                model_name=model_name
            )
            
            end_time = time.time()
            duracao_segundos = end_time - start_time
            
            tokens_entrada = resposta_llm.get('usage', {}).get('prompt_tokens', 0)
            tokens_saida = resposta_llm.get('usage', {}).get('completion_tokens', 0)
            modelo_final = resposta_llm.get('model', model_name or llm_model or 'unknown')
            tipo_tarefa = status_update or 'revisao_codigo'
            job_id_final = job_id or 'unknown'
            projeto_final = projeto or 'unknown'
            
            print(f"[DEBUG] Dados preparados para logging:")
            print(f"  - projeto_final: {projeto_final}")
            print(f"  - tipo_tarefa: {tipo_tarefa}")
            print(f"  - modelo_final: {modelo_final}")
            print(f"  - tokens_entrada: {tokens_entrada}")
            print(f"  - tokens_saida: {tokens_saida}")
            print(f"  - job_id_final: {job_id_final}")
            print(f"  - duracao_segundos: {duracao_segundos}")
            
            if self.validate_logging_fields(projeto_final, tipo_tarefa, modelo_final, 
                                          tokens_entrada, tokens_saida, job_id_final):
                try:
                    log_tokens(
                        projeto=projeto_final,
                        tipo_tarefa=tipo_tarefa,
                        modelo=modelo_final,
                        tokens_entrada=tokens_entrada,
                        tokens_saida=tokens_saida,
                        duracao_segundos=duracao_segundos,
                        job_id=job_id_final
                    )
                    print(f"[DEBUG] log_tokens executado com sucesso")
                except Exception as e:
                    print(f"[ERRO] Falha ao executar log_tokens: {e}")
            else:
                print(f"[ERRO] Validação de campos falhou, log_tokens não será executado")
            
            return {
                "resultado": {
                    "reposta_final": resposta_llm
                }
            }
            
        except Exception as e:
            print(f"[ERRO] Erro durante execução do AgenteRevisor: {e}")
            raise