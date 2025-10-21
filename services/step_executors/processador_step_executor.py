import re
import json
import time
from typing import Dict, Any
from services.step_executors.base_step_executor import BaseStepExecutor
from services.factories.agent_factory import AgentFactory
from tools.readers.reader_geral import ReaderGeral
from services.report_handler import ReportHandler
from models import JobFields

class ProcessadorStepExecutor(BaseStepExecutor):
    def __init__(self, job_handler):
        self.job_handler = job_handler
    
    def execute(self, job_id: str, job_info: Dict[str, Any], step: Dict[str, Any], 
                current_step_index: int, previous_step_result: Dict[str, Any], 
                repo_reader: ReaderGeral, llm_provider, agent_params: Dict[str, Any]) -> Dict[str, Any]:
        
        instrucoes_formatadas = job_info['data'].get('instrucoes_extras') or ''
        instrucoes_formatadas += "\n\n---\n\nCONTEXTO DA ETAPA ANTERIOR:\n"
        instrucoes_formatadas += json.dumps(previous_step_result, indent=2, ensure_ascii=False)

        observacoes_humanas = self.job_handler.get_approval_instructions(job_info)
        if observacoes_humanas:
            instrucoes_formatadas += f"\n\n---\n\nOBSERVAÇÕES ADICIONAIS DO USUÁRIO NA APROVAÇÃO:\n{observacoes_humanas}"
            print(f"[{job_id}] Aplicando instruções extras de aprovação na etapa {current_step_index}: {observacoes_humanas[:100]}...")
            self.job_handler.clear_approval_instructions(job_info)
            self.job_handler.update_job(job_id, job_info)

        agent_params['instrucoes_extras'] = instrucoes_formatadas
        agent_params.update({
            'codigo': previous_step_result,
            'repositorio': job_info['data']['repo_name'],
            'nome_branch': job_info['data']['branch_name'],
            'repository_type': job_info['data']['repository_type']
        })
        
        agent_params['retornar_lista_arquivos'] = agent_params.get('retornar_lista_arquivos', False)
        if isinstance(previous_step_result, dict) and 'lista_arquivos' in previous_step_result:
            agent_params['lista_arquivos'] = previous_step_result['lista_arquivos']
        agent_params['modo_adicao_incremental'] = agent_params.get('modo_adicao_incremental', False)

        transcricao_reuniao = job_info['data'].get('transcricao_reuniao') or None
        if transcricao_reuniao is not None:
            agent_params['transcricao_reuniao'] = transcricao_reuniao

        max_retries = 2
        for attempt in range(max_retries):
            try:
                agente = AgentFactory.create_agent("processador", None, llm_provider)
                agent_response = agente.main(**agent_params)
                if not agent_response or not agent_response.get('resultado', {}).get('reposta_final'):
                    print(f"[{job_id}] AVISO: agent_response não contém 'resultado.reposta_final'. Resposta: {agent_response}")
                    if previous_step_result and isinstance(previous_step_result, dict) and previous_step_result:
                        print(f"[{job_id}] A IA retornou resposta vazia ou inválida. Reutilizando resultado anterior.")
                        return previous_step_result
                    raise ValueError("IA retornou resposta vazia ou inválida e não há resultado anterior para usar.")
                raw_response_from_llm = agent_response.get('resultado', {}).get('reposta_final', {}).get('reposta_final', '')

                cleaned_string = None
                match = re.search(r"\s*([\s\S]*?)\s*", raw_response_from_llm)
                if match:
                    cleaned_string = match.group(1).strip()
                    print(f"[{job_id}] {cleaned_string}")
                else:
                    start = raw_response_from_llm.find('{')
                    end = raw_response_from_llm.rfind('}')
                    if start != -1 and end != -1:
                        cleaned_string = raw_response_from_llm[start:end+1]

                if not cleaned_string:
                    if previous_step_result and isinstance(previous_step_result, dict) and previous_step_result:
                        print(f"[{job_id}] A IA retornou resposta vazia ou inválida. Reutilizando resultado anterior.")
                        return previous_step_result
                    raise ValueError("IA retornou resposta vazia ou inválida e não há resultado anterior para usar.")

                result = json.loads(cleaned_string, strict=False)
                print(f"[{job_id}] JSON decodificado com sucesso na tentativa {attempt + 1}.")

                # Passo 3: Salvar JSON de tarefas diretamente no analysis_report se tipo de análise for geração de tarefas
                tipo_analise = job_info['data'].get('original_analysis_type')
                if tipo_analise and ('tarefa' in tipo_analise or 'geracao_tarefas' in tipo_analise or 'tasks' in tipo_analise):
                    job_info['data']['analysis_report'] = json.dumps(result, ensure_ascii=False)
                    self.job_handler.update_job(job_id, job_info)
                else:
                    report_text = ReportHandler.extract_report_text(result)
                    if report_text and isinstance(report_text, str) and report_text.strip():
                        job_info['data']['analysis_report'] = report_text
                        self.job_handler.update_job(job_id, job_info)
                    else:
                        print(f"[{job_id}] AVISO: ReportHandler.extract_report_text retornou vazio ou None. Nenhum relatório salvo.")
                return result
                
            except (json.JSONDecodeError, ValueError) as e:
                print(f"[{job_id}] Tentativa {attempt + 1}/{max_retries} falhou: {e}")
                if attempt + 1 == max_retries:
                    print(f"[{job_id}] ERRO: Máximo de tentativas atingido. Falhando o step.")
                    raise e
                time.sleep(5)
