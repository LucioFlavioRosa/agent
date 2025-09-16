import json
from typing import Dict, Any, Optional
from domain.interfaces.workflow_orchestrator_interface import IWorkflowOrchestrator
from domain.interfaces.job_manager_interface import IJobManager
from domain.interfaces.blob_storage_interface import IBlobStorageService
from services.factories.llm_provider_factory import LLMProviderFactory
from services.factories.agent_factory import AgentFactory
from services.job_handler import JobHandler
from services.report_handler import ReportHandler
from services.commit_handler import CommitHandler
from services.data_formatter import DataFormatter
from tools.rag_retriever import AzureAISearchRAGRetriever
from tools.readers.reader_geral import ReaderGeral
from tools.repository_provider_factory import get_repository_provider_explicit

class WorkflowOrchestrator(IWorkflowOrchestrator):
    def __init__(self, job_manager: IJobManager, blob_storage: IBlobStorageService, 
                 workflow_registry: Dict[str, Any], rag_retriever=None, 
                 job_handler: JobHandler = None, report_handler: ReportHandler = None,
                 commit_handler: CommitHandler = None, data_formatter: DataFormatter = None):
        self.workflow_registry = workflow_registry
        self.rag_retriever = rag_retriever or AzureAISearchRAGRetriever()
        
        self.job_handler = job_handler or JobHandler(job_manager)
        self.report_handler = report_handler or ReportHandler(blob_storage)
        self.commit_handler = commit_handler or CommitHandler()
        self.data_formatter = data_formatter or DataFormatter()

    def execute_workflow(self, job_id: str, start_from_step: int = 0) -> None:
        job_info = self.job_handler.get_job_info(job_id)

        workflow = self.workflow_registry.get(job_info['data']['original_analysis_type'])
        if not workflow:
            raise ValueError("Workflow não encontrado.")
            
        try:
            repository_type = job_info['data']['repository_type']
            repo_name = job_info['data']['repo_name']
            repository_provider = get_repository_provider_explicit(repository_type)
            repo_reader = ReaderGeral(repository_provider=repository_provider)

            previous_step_result = self.job_handler.get_step_result(job_info, start_from_step)
            steps_to_run = workflow.get('steps', [])[start_from_step:]

            for i, step in enumerate(steps_to_run):
                current_step_index = start_from_step + i
                self.job_handler.update_job_status(job_id, step['status_update'])

                if current_step_index == 0:
                    existing_report_result = self.report_handler.try_read_existing_report(job_id, job_info, current_step_index)
                    if existing_report_result:
                        print(f"[{job_id}] Relatório existente encontrado no Blob Storage")

                        report_data = json.loads(existing_report_result['resultado']['reposta_final']['reposta_final'])
                        report_text = report_data.get('relatorio', '')

                        job_info['data']['analysis_report'] = report_text
                        self.job_handler.save_step_result(job_info, current_step_index, report_data)

                        if self.job_handler.should_generate_report_only(job_info, current_step_index):
                            print(f"[{job_id}] Modo 'gerar_relatorio_apenas' ativo com relatório existente. Finalizando.")
                            self.job_handler.update_job_status(job_id, 'completed')
                            return

                        if step.get('requires_approval'):
                            print(f"[{job_id}] Relatório existente carregado. Pausando para aprovação do usuário.")
                            self.handle_approval_step(job_id, job_info, current_step_index, report_data)
                            return

                        previous_step_result = report_data
                        continue
                    else:
                        print(f"[{job_id}] Relatório não encontrado no Blob Storage, gerando novo relatório via agente")

                step_result = self._execute_step(job_id, job_info, step, current_step_index, 
                                               previous_step_result, repo_reader, i, start_from_step)

                self.job_handler.save_step_result(job_info, current_step_index, step_result)
                previous_step_result = step_result

                if self.job_handler.should_generate_report_only(job_info, current_step_index):
                    self.report_handler.handle_report_only_mode(job_id, job_info, step_result)
                    self.job_handler.update_job_status(job_id, 'completed')
                    return

                if step.get('requires_approval'):
                    self.handle_approval_step(job_id, job_info, current_step_index, step_result)
                    return

            self._finalize_workflow(job_id, job_info, workflow, previous_step_result, repository_type, repo_name)

        except Exception as e:
            self.job_handler.handle_job_error(job_id, e, 'workflow')

    def _execute_step(self, job_id: str, job_info: Dict[str, Any], step: Dict[str, Any], 
                     current_step_index: int, previous_step_result: Dict[str, Any], 
                     repo_reader: ReaderGeral, step_iteration: int, start_from_step: int) -> Dict[str, Any]:

        model_para_etapa = step.get('model_name', job_info.get('data', {}).get('model_name'))
        llm_provider = LLMProviderFactory.create_provider(model_para_etapa, self.rag_retriever)
        agent_params = step.get('params', {}).copy()
        agent_params.update({
            'usar_rag': job_info.get("data", {}).get("usar_rag", False), 
            'model_name': model_para_etapa
        })

        input_para_agente_final = {}

        if current_step_index == 0:
            instrucoes = job_info['data'].get('instrucoes_extras')
            input_para_agente_final = {"instrucoes_iniciais": instrucoes}
        else:
            input_para_agente_final = {"instrucoes_iniciais": previous_step_result}

        agent_type = step.get("agent_type")
        agente = AgentFactory.create_agent(agent_type, repo_reader, llm_provider)

        if agent_type == "revisor":
            instrucoes_formatadas = job_info['data'].get('instrucoes_extras', '')
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
                                    'repositorio': job_info['data']['repo_name'],
                                    'nome_branch': job_info['data']['branch_name'], 
                                    'instrucoes_extras': instrucoes_formatadas,
                                    'arquivos_especificos': job_info['data'].get('arquivos_especificos'),
                                    'repository_type': job_info['data']['repository_type'],
                                    'job_id': job_id,
                                    'projeto': job_info['data']['projeto'],
                                    'status_update': step['status_update']
                                })

        elif agent_type == "processador":
            instrucoes_extras = job_info['data'].get('instrucoes_extras')
            observacoes_humanas = self.job_handler.get_approval_instructions(job_info)
            
            if instrucoes_extras or observacoes_humanas:
                if isinstance(input_para_agente_final.get('instrucoes_iniciais'), dict):
                    if instrucoes_extras:
                        input_para_agente_final['instrucoes_iniciais']['instrucoes_extras'] = instrucoes_extras
                    if observacoes_humanas:
                        input_para_agente_final['instrucoes_iniciais']['observacoes_aprovacao'] = observacoes_humanas
                elif isinstance(input_para_agente_final.get('instrucoes_iniciais'), str):
                    if instrucoes_extras:
                        input_para_agente_final['instrucoes_iniciais'] += f"\n\n---\n\nINSTRUÇÕES EXTRAS DO USUÁRIO:\n{instrucoes_extras}"
                    if observacoes_humanas:
                        input_para_agente_final['instrucoes_iniciais'] += f"\n\n---\n\nOBSERVAÇÕES ADICIONAIS DO USUÁRIO NA APROVAÇÃO:\n{observacoes_humanas}"
                else:
                    if instrucoes_extras:
                        input_para_agente_final['instrucoes_extras'] = instrucoes_extras
                    if observacoes_humanas:
                        input_para_agente_final['observacoes_aprovacao'] = observacoes_humanas
                
                if observacoes_humanas:
                    print(f"[{job_id}] Aplicando instruções extras de aprovação no processador da etapa {current_step_index}: {observacoes_humanas[:100]}...")
                    self.job_handler.clear_approval_instructions(job_info)
                    self.job_handler.update_job(job_id, job_info)

            agent_params['codigo'] = input_para_agente_final

        else:
            raise ValueError(f"Tipo de agente desconhecido '{agent_type}'.")

        agent_params['repository_type'] = job_info['data']['repository_type']

        agent_response = agente.main(**agent_params)

        json_string = agent_response.get('resultado', {}).get('reposta_final', {}).get('reposta_final', '')

        cleaned_string = json.loads(json_string.replace("```json", "").replace("```", "").strip())

        if not cleaned_string:
            if previous_step_result and isinstance(previous_step_result, dict):
                print(f"[{job_id}] A IA retornou resposta vazia. Reutilizando resultado anterior.")
                return previous_step_result
            raise ValueError("IA retornou resposta vazia e não há resultado anterior para usar.")

        return json.loads(cleaned_string)

    def handle_approval_step(self, job_id: str, job_info: Dict[str, Any], step_index: int, step_result: Dict[str, Any]) -> None:
        print(f"[{job_id}] Etapa requer aprovação.")

        report_text = self.report_handler.extract_report_text(step_result)
        job_info['data']['analysis_report'] = report_text

        if job_info['data'].get('gerar_novo_relatorio', True):
            self.report_handler.save_report_to_blob(job_id, job_info, report_text, report_generated_by_agent=True)
        else:
            print(f"[{job_id}] gerar_novo_relatorio=False - Não salvando relatório no Blob Storage")

        job_info['status'] = 'pending_approval'
        self.job_handler.set_paused_step(job_info, step_index)
        self.job_handler.update_job(job_id, job_info)

    def _finalize_workflow(self, job_id: str, job_info: Dict[str, Any], workflow: Dict[str, Any], 
                          final_result: Dict[str, Any], repository_type: str, repo_name: str) -> None:

        resultado_agrupamento, resultado_refatoracao = self.data_formatter.extract_workflow_results(
            job_info, workflow, final_result
        )

        job_info['data']['diagnostic_logs'] = {
            "penultimate_result": resultado_refatoracao,
            "final_result": resultado_agrupamento
        }

        self.job_handler.update_job_status(job_id, 'populating_data')

        dados_preenchidos = self.data_formatter.populate_changeset_data(
            resultado_agrupamento, resultado_refatoracao
        )

        dados_finais_formatados = self.data_formatter.format_final_data(dados_preenchidos)

        self.job_handler.update_job_status(job_id, 'committing_to_github')

        self.commit_handler.execute_commits(job_id, job_info, dados_finais_formatados, repository_type, repo_name)

        self.job_handler.update_job_status(job_id, 'completed')
        print(f"[{job_id}] Processo concluído com sucesso!")
