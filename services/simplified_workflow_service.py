from typing import Any, Dict
from models import AnalysisRequest
from tools.readers.reader_geral import ReaderGeral
from services.job_handler import JobHandler
from services.workflow_registry_service import WorkflowRegistryService
from tools.repository_provider_factory import get_repository_provider_explicit

class SimplifiedWorkflowService:
    def __init__(self, job_handler: JobHandler = None, workflow_registry_service: WorkflowRegistryService = None):
        self.job_handler = job_handler or JobHandler()
        self.workflow_registry_service = workflow_registry_service or WorkflowRegistryService()

    def start_analysis(self, analysis_request: AnalysisRequest) -> str:
        """
        Inicia uma análise de revisão ou melhoria de código.
        :param analysis_request: Instância de AnalysisRequest contendo dados da análise.
        :return: job_id
        :raises Exception: se não for possível acessar o repositório
        """
        # Validação mínima dos campos obrigatórios
        if not analysis_request.repository_type or not analysis_request.repo_name or not analysis_request.branch_name:
            raise ValueError("repository_type, repo_name e branch_name são obrigatórios.")

        # Criação do job
        job_data = {
            'repository_type': analysis_request.repository_type,
            'repo_name': analysis_request.repo_name,
            'branch_name': analysis_request.branch_name,
            'agent_type': analysis_request.agent_type,
            'arquivos_especificos': analysis_request.arquivos_especificos,
            'instrucoes_extras': analysis_request.instrucoes_extras
        }
        job_id = self.job_handler.create_job(job_data)

        # Instancia ReaderGeral para acesso ao repositório
        repository_provider = get_repository_provider_explicit(analysis_request.repository_type)
        repo_reader = ReaderGeral(repository_provider=repository_provider)

        # Valida acesso ao repositório
        if not repo_reader.validate_repository_access(analysis_request.repo_name, analysis_request.branch_name):
            self.job_handler.update_job_status(job_id, 'failed')
            self.job_handler.update_job(job_id, {'error_details': 'Falha ao acessar o repositório.'})
            raise Exception('Falha ao acessar o repositório. Verifique permissões e dados informados.')

        # Lê o código do repositório antes de iniciar a análise
        repo_reader.read_repository(analysis_request.repo_name, analysis_request.branch_name)

        # O agente SEMPRE recebe o repositório como entrada
        # Não há mais lógica para agentes que não recebem repositório

        # Retorna o job_id para acompanhamento
        return job_id
