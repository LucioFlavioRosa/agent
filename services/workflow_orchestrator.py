import json
from typing import Dict, Any, Optional
from domain.interfaces.workflow_orchestrator_interface import IWorkflowOrchestrator
from domain.interfaces.job_manager_interface import IJobManager
from domain.interfaces.blob_storage_interface import IBlobStorageService
from services.factories.llm_provider_factory import LLMProviderFactory
from services.factories.agent_factory import AgentFactory
from tools.rag_retriever import AzureAISearchRAGRetriever
from tools.preenchimento import ChangesetFiller
from tools.readers.reader_geral import ReaderGeral
from tools.conectores.conexao_geral import ConexaoGeral
from tools.repo_committers.orchestrator import processar_branch_por_provedor
from tools.repository_provider_factory import get_repository_provider_explicit

class WorkflowOrchestrator(IWorkflowOrchestrator):
    def __init__(self, job_manager: IJobManager, blob_storage: IBlobStorageService, 
                 workflow_registry: Dict[str, Any]):
        self.job_manager = job_manager
        self.blob_storage = blob_storage
        self.workflow_registry = workflow_registry
        self.rag_retriever = AzureAISearchRAGRetriever()
        self.changeset_filler = ChangesetFiller()

    def execute_workflow(self, job_id: str, start_from_step: int = 0) -> None:
        try:
            job_info = self.job_manager.get_job(job_id)
            if not job_info:
                raise ValueError("Job não encontrado.")

            # NOVA LÓGICA: Verificar se deve usar relatório existente antes de executar qualquer step
            if start_from_step == 0 and not job_info['data'].get('gerar_novo_relatorio', True):
                existing_report = self._try_use_existing_report(job_id, job_info)
                if existing_report:
                    return  # Workflow finalizado com relatório existente

            workflow = self.workflow_registry.get(job_info['data']['original_analysis_type'])
            if not workflow:
                raise ValueError("Workflow não encontrado.")

            repository_type = job_info['data']['repository_type']
            repo_name = job_info['data']['repo_name']
            repository_provider = get_repository_provider_explicit(repository_type)
            repo_reader = ReaderGeral(repository_provider=repository_provider)

            previous_step_result = job_info['data'].get(f'step_{start_from_step - 1}_result', {})
            steps_to_run = workflow.get('steps', [])[start_from_step:]

            for i, step in enumerate(steps_to_run):
                current_step_index = start_from_step + i
                self.job_manager.update_job_status(job_id, step['status_update'])

                step_result = self._execute_step(job_id, job_info, step, current_step_index, 
                                               previous_step_result, repo_reader, i, start_from_step)

                job_info['data'][f'step_{current_step_index}_result'] = step_result
                previous_step_result = step_result

                if self._should_generate_report_only(job_info, current_step_index):
                    self._handle_report_only_mode(job_id, job_info, step_result)
                    return

                if step.get('requires_approval'):
                    # Agora passando a versão mais atual do job_info
                    self.handle_approval_step(job_id, job_info, current_step_index, step_result)
                    return

            self._finalize_workflow(job_id, job_info, workflow, previous_step_result, repository_type, repo_name)

        except Exception as e:
            self.job_manager.handle_job_error(job_id, e, 'workflow')

    def _try_use_existing_report(self, job_id: str, job_info: Dict[str, Any]) -> bool:
        """Tenta usar um relatório existente do Blob Storage. Retorna True se encontrou e finalizou o workflow."""
        analysis_name = job_info['data'].get('analysis_name')
        if not analysis_name:
            print(f"[{job_id}] Sem analysis_name definido, não é possível buscar relatório existente")
            return False

        print(f"[{job_id}] Tentando ler relatório existente do Blob Storage: {analysis_name}")
        
        try:
            existing_report = self.blob_storage.read_report(
                job_info['data']['projeto'],
                job_info['data']['original_analysis_type'],
                job_info['data']['repository_type'],
                job_info['data']['repo_name'],
                job_info['data'].get('branch_name', 'main'),
                analysis_name
            )

            if existing_report:
                print(f"[{job_id}] Relatório encontrado no Blob Storage, usando relatório existente")
                
                # Preencher dados do job com o relatório existente
                job_info['data']['analysis_report'] = existing_report
                
                # Construir URL do blob (assumindo que existe se conseguimos ler)
                from tools.blob_report_path_builder import build_report_blob_path
                blob_path = build_report_blob_path(
                    job_info['data']['projeto'],
                    job_info['data']['original_analysis_type'],
                    job_info['data']['repository_type'],
                    job_info['data']['repo_name'],
                    job_info['data'].get('branch_name', 'main'),
                    analysis_name
                )
                # Construir URL completa do blob (isso pode variar dependendo da implementação do blob storage)
                job_info['data']['report_blob_url'] = f"https://storage.blob.core.windows.net/{blob_path}"
                
                # Finalizar workflow como completed
                job_info['status'] = 'completed'
                self.job_manager.update_job(job_id, job_info)
                
                print(f"[{job_id}] Workflow finalizado com relatório existente")
                return True
            else:
                print(f"[{job_id}] Relatório não encontrado no Blob Storage, gerando novo relatório via agente")
                return False
                
        except Exception as e:
            print(f"[{job_id}] Erro ao tentar ler relatório existente: {e}. Gerando novo relatório via agente")
            return False

    # Substitua todo o seu método _execute_step por este

    def _execute_step(self, job_id: str, job_info: Dict[str, Any], step: Dict[str, Any], 
                     current_step_index: int, previous_step_result: Dict[str, Any], 
                     repo_reader: ReaderGeral, step_iteration: int, start_from_step: int) -> Dict[str, Any]:
    
        # --- 1. Preparação do Agente ---
        model_para_etapa = step.get('model_name', job_info.get('data', {}).get('model_name'))
        llm_provider = LLMProviderFactory.create_provider(model_para_etapa, self.rag_retriever)
        agent_params = step.get('params', {}).copy()
        agent_params.update({
            'usar_rag': job_info.get("data", {}).get("usar_rag", False), 
            'model_name': model_para_etapa
        })
    
        # --- 2. Preparação CONSISTENTE do Input ---
        input_para_agente_final = {}
        
        # Se for a primeira etapa, o input são as instruções originais do usuário.
        if current_step_index == 0:
            instrucoes = job_info['data'].get('instrucoes_extras')
            input_para_agente_final = {"instrucoes_iniciais": instrucoes}
        else:
            # Nas etapas seguintes, o input é o resultado da etapa anterior.
            # Nós o re-empacotamos no formato que o agente 'processador' espera.
            input_para_agente_final = {"instrucoes_iniciais": previous_step_result}
    
        # --- 3. Execução do Agente ---
        agent_type = step.get("agent_type")
        agente = AgentFactory.create_agent(agent_type, repo_reader, llm_provider)
    
        if agent_type == "revisor":
            # Esta lógica é para workflows que usam o 'revisor' em etapas > 0
            instrucoes_formatadas = job_info['data'].get('instrucoes_extras', '')
            instrucoes_formatadas += "\n\n---\n\nCONTEXTO DA ETAPA ANTERIOR:\n"
            # Usamos o resultado puro da etapa anterior
            instrucoes_formatadas += json.dumps(previous_step_result, indent=2, ensure_ascii=False)
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
            # O processador recebe o input já formatado corretamente
            agent_params['codigo'] = input_para_agente_final
    
        else:
            raise ValueError(f"Tipo de agente desconhecido '{agent_type}'.")
    
        # Atualiza os outros parâmetros
        agent_params['repository_type'] = job_info['data']['repository_type']
        
        agent_response = agente.main(**agent_params)
        
        # --- 4. Processamento da Resposta ---
        json_string = agent_response.get('resultado', {}).get('reposta_final', {}).get('reposta_final', '')
        cleaned_string = json_string.replace("", "").replace("", "").strip()
        
        if not cleaned_string:
            if previous_step_result and isinstance(previous_step_result, dict):
                print(f"[{job_id}] A IA retornou resposta vazia. Reutilizando resultado anterior.")
                return previous_step_result
            raise ValueError("IA retornou resposta vazia e não há resultado anterior para usar.")
            
        return json.loads(cleaned_string)
                         
    def _try_read_existing_report(self, job_id: str, job_info: Dict[str, Any], current_step_index: int) -> Optional[Dict[str, Any]]:
        # MÉTODO REMOVIDO - A lógica foi centralizada em _try_use_existing_report
        return None

    def _execute_agent(self, job_id: str, job_info: Dict[str, Any], step: Dict[str, Any], 
                      agent_params: Dict[str, Any], input_para_etapa: Dict[str, Any], 
                      current_step_index: int, repo_reader: ReaderGeral, llm_provider) -> Dict[str, Any]:

        agent_type = step.get("agent_type")
        agente = AgentFactory.create_agent(agent_type, repo_reader, llm_provider)

        if agent_type == "revisor":
            instrucoes = job_info['data'].get('instrucoes_extras', '')
            
            if current_step_index > 0:
                instrucoes += "\n\n---\n\nCONTEXTO DA ETAPA ANTERIOR (APROVADO PELO USUÁRIO):\n"
                instrucoes += json.dumps(input_para_etapa, indent=2, ensure_ascii=False)
                
            observacoes_humanas = job_info['data'].get('instrucoes_extras_aprovacao')
            if observacoes_humanas:
                instrucoes += f"\n\n---\n\nOBSERVAÇÕES ADICIONAIS DO USUÁRIO NA APROVAÇÃO:\n{observacoes_humanas}"

            agent_params.update({
                'repositorio': job_info['data']['repo_name'], 
                'nome_branch': job_info['data']['branch_name'], 
                'instrucoes_extras': instrucoes,
                'arquivos_especificos': job_info['data'].get('arquivos_especificos'),
                'repository_type': job_info['data']['repository_type'],
                'job_id': job_id,
                'projeto': job_info['data']['projeto'],
                'status_update': step['status_update']
            })
            return agente.main(**agent_params)
            
        elif agent_type == "processador":
            input_final_para_agente = {}
        
            # Se for a primeira etapa do workflow, o input são as instruções originais do usuário.
            if current_step_index == 0:
                input_final_para_agente = {"instrucoes_iniciais": job_info['data'].get('instrucoes_extras')}
            else:
                # Nas etapas seguintes, o input principal deve ser o resultado da etapa anterior.
                resultado_anterior = input_para_etapa
                
                # VERIFICA e DESEMPACOTA o resultado se ele vier da etapa de aprovação.
                if isinstance(input_para_etapa, dict) and "resultado_etapa_anterior" in input_para_etapa:
                    resultado_anterior = input_para_etapa.get("resultado_etapa_anterior")
                
                # Remonta o dicionário na estrutura que o agente espera,
                # usando o resultado anterior (o relatório) como a instrução.
                input_final_para_agente = {"instrucoes_iniciais": resultado_anterior}
        
            agent_params['codigo'] = input_final_para_agente
            agent_params['repository_type'] = job_info['data']['repository_type']
            return agente.main(**agent_params)

        raise ValueError(f"Tipo de agente desconhecido '{agent_type}'.")

    def _should_generate_report_only(self, job_info: Dict[str, Any], current_step_index: int) -> bool:
        return current_step_index == 0 and job_info['data'].get('gerar_relatorio_apenas') is True
    
    def _handle_report_only_mode(self, job_id: str, job_info: Dict[str, Any], step_result: Dict[str, Any]) -> None:
        report_text = step_result.get("relatorio", json.dumps(step_result, indent=2, ensure_ascii=False))
        job_info['data']['analysis_report'] = report_text

        self._save_report_to_blob(job_id, job_info, report_text, report_generated_by_agent=True)

        print(f"[{job_id}] Modo 'gerar_relatorio_apenas' ativo. Finalizando.")
        self.job_manager.update_job_status(job_id, 'completed')

    def handle_approval_step(self, job_id: str, job_info: Dict[str, Any], step_index: int, step_result: Dict[str, Any]) -> None:
        print(f"[{job_id}] Etapa requer aprovação.")

        #job_info = self.job_manager.get_job(job_id)
        report_text = step_result.get("relatorio", json.dumps(step_result, indent=2, ensure_ascii=False))
        job_info['data']['analysis_report'] = report_text

        self._save_report_to_blob(job_id, job_info, report_text, report_generated_by_agent=True)

        job_info['status'] = 'pending_approval'
        job_info['data']['paused_at_step'] = step_index
        self.job_manager.update_job(job_id, job_info)

    def _save_report_to_blob(self, job_id: str, job_info: Dict[str, Any], report_text: str, report_generated_by_agent: bool) -> None:
        # AJUSTE: Só salva no Blob Storage se o relatório foi realmente gerado por um agente
        if job_info['data'].get('analysis_name') and report_text and report_generated_by_agent:
            try:
                blob_url = self.blob_storage.upload_report(
                    report_text,
                    job_info['data']['projeto'],
                    job_info['data']['original_analysis_type'],
                    job_info['data']['repository_type'],
                    job_info['data']['repo_name'],
                    job_info['data'].get('branch_name', 'main'),
                    job_info['data']['analysis_name']
                )
                job_info['data']['report_blob_url'] = blob_url
                print(f"[{job_id}] Relatório salvo no Blob Storage: {blob_url}")
            except Exception as e:
                print(f"[{job_id}] Erro ao salvar relatório no Blob Storage: {e}")

    def _finalize_workflow(self, job_id: str, job_info: Dict[str, Any], workflow: Dict[str, Any], 
                          final_result: Dict[str, Any], repository_type: str, repo_name: str) -> None:

        workflow_steps = workflow.get("steps", [])
        num_total_steps = len(workflow_steps)

        resultado_agrupamento = final_result
        resultado_refatoracao = {}

        if num_total_steps >= 2:
            penultimate_step_index = num_total_steps - 2
            resultado_refatoracao = job_info['data'].get(f'step_{penultimate_step_index}_result', {})
        elif num_total_steps == 1:
            resultado_refatoracao = final_result

        job_info['data']['diagnostic_logs'] = {
            "penultimate_result": resultado_refatoracao,
            "final_result": resultado_agrupamento
        }

        self.job_manager.update_job_status(job_id, 'populating_data')

        dados_preenchidos = self.changeset_filler.main(
            json_agrupado=resultado_agrupamento,
            json_inicial=resultado_refatoracao
        )

        dados_finais_formatados = self._format_final_data(dados_preenchidos)

        self.job_manager.update_job_status(job_id, 'committing_to_github')

        self._execute_commits(job_id, job_info, dados_finais_formatados, repository_type, repo_name)

        self.job_manager.update_job_status(job_id, 'completed')
        print(f"[{job_id}] Processo concluído com sucesso!")

    def _format_final_data(self, dados_preenchidos: Dict[str, Any]) -> Dict[str, Any]:
        dados_finais_formatados = {"resumo_geral": dados_preenchidos.get("resumo_geral", ""), "grupos": []}

        for nome_grupo, detalhes_pr in dados_preenchidos.items():
            if nome_grupo == "resumo_geral":
                continue
            dados_finais_formatados["grupos"].append({
                "branch_sugerida": nome_grupo, 
                "titulo_pr": detalhes_pr.get("resumo_do_pr", ""), 
                "resumo_do_pr": detalhes_pr.get("descricao_do_pr", ""), 
                "conjunto_de_mudancas": detalhes_pr.get("conjunto_de_mudancas", [])
            })

        return dados_finais_formatados

    def _execute_commits(self, job_id: str, job_info: Dict[str, Any], dados_finais_formatados: Dict[str, Any], 
                        repository_type: str, repo_name: str) -> None:

        branch_base_para_pr = job_info['data'].get('branch_name', 'main')

        print(f"[{job_id}] Iniciando commit com repositório: '{repo_name}' (tipo: {repository_type})")

        repository_provider = get_repository_provider_explicit(repository_type)
        conexao_geral = ConexaoGeral.create_with_defaults()
        repo = conexao_geral.connection(
            repositorio=repo_name,
            repository_type=repository_type,
            repository_provider=repository_provider
        )

        commit_results = []
        for grupo in dados_finais_formatados["grupos"]:
            resultado_branch = processar_branch_por_provedor(
                repo=repo,
                nome_branch=grupo["branch_sugerida"],
                branch_de_origem=branch_base_para_pr,
                branch_alvo_do_pr=branch_base_para_pr,
                mensagem_pr=grupo["titulo_pr"],
                descricao_pr=grupo["resumo_do_pr"],
                conjunto_de_mudancas=grupo["conjunto_de_mudancas"],
                repository_type=repository_type
            )
            commit_results.append(resultado_branch)

        print(f"[{job_id}] Commit concluído. Resultados: {len(commit_results)} branches processadas")
        job_info['data']['commit_details'] = commit_results
        self.job_manager.update_job(job_id, job_info)