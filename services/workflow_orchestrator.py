from typing import Any, Dict

class WorkflowOrchestrator:
    def __init__(self, job_manager, blob_storage, workflow_registry, rag_retriever, job_handler, report_handler, commit_handler, data_formatter):
        self.job_manager = job_manager
        self.blob_storage = blob_storage
        self.workflow_registry = workflow_registry
        self.rag_retriever = rag_retriever
        self.job_handler = job_handler
        self.report_handler = report_handler
        self.commit_handler = commit_handler
        self.data_formatter = data_formatter

    def execute_workflow(self, job_id: str, start_from_step: int = 0):
        job_info = self.job_manager.get_job(job_id)
        # ... (demais etapas do workflow)
        # Supondo que dados_finais_formatados é gerado por algum método
        dados_finais_formatados = self.data_formatter.format_data_for_commit(job_id, job_info)
        # Validação antes de chamar execute_commits
        if not dados_finais_formatados or 'grupos' not in dados_finais_formatados or not isinstance(dados_finais_formatados['grupos'], list) or len(dados_finais_formatados['grupos']) == 0:
            print(f"[{job_id}] [ERRO] Estrutura de dados_finais_formatados inválida ou grupos vazio/malformado: {dados_finais_formatados}")
            if 'data' in job_info:
                job_info['data']['commit_details'] = [{
                    "branch_name": "erro-formato",
                    "success": False,
                    "pr_url": "ERRO: Estrutura de entrada de dados_finais_formatados['grupos'] está vazia, ausente ou malformada.",
                    "message": "Estrutura de entrada de grupos está vazia, ausente ou malformada.",
                    "arquivos_modificados": [],
                    "commit_url": None
                }]
                job_info['data']['status'] = 'failed'
                job_info['data']['error_details'] = 'Estrutura de dados_finais_formatados inválida ou grupos vazio/malformado.'
            else:
                job_info['commit_details'] = [{
                    "branch_name": "erro-formato",
                    "success": False,
                    "pr_url": "ERRO: Estrutura de entrada de dados_finais_formatados['grupos'] está vazia, ausente ou malformada.",
                    "message": "Estrutura de entrada de grupos está vazia, ausente ou malformada.",
                    "arquivos_modificados": [],
                    "commit_url": None
                }]
                job_info['status'] = 'failed'
                job_info['error_details'] = 'Estrutura de dados_finais_formatados inválida ou grupos vazio/malformado.'
            self.job_manager.set_job(job_id, job_info)
            print(f"[{job_id}] [ERRO] Commit não será executado devido a dados inválidos.")
            return
        self.commit_handler.execute_commits(
            job_id=job_id,
            job_info=job_info,
            dados_finais_formatados=dados_finais_formatados,
            repository_type=job_info['data'].get('repository_type'),
            repo_name=job_info['data'].get('repo_name'),
            usuario_executor=job_info['data'].get('usuario_executor')
        )
        self.job_manager.set_job(job_id, job_info)
