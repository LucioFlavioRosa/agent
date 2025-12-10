from services.response_builder_service import ResponseBuilderService
from services.pull_request_extractor_service import PullRequestExtractorService
from services.job_logging_service import JobLoggingService
from services.repository_normalizer_service import RepositoryNormalizerService
from services.job_data_service import JobDataService
from services.job_validation_service import JobValidationService

class ApiServiceFactory:
    """Factory para criação e configuração de serviços da API."""
    
    def __init__(self, pr_extractor, logging_service):
        self._pr_extractor_service = None
        self._logging_service = None
        self._response_builder_service = None
        self._repository_normalizer_service = None
        self._job_data_service = None
        self._job_validation_service = None
        self.pr_extractor = pr_extractor
        self.logging_service = logging_service
    
    def get_pr_extractor_service(self) -> PullRequestExtractorService:
        """Retorna instância do serviço de extração de PRs."""
        if self._pr_extractor_service is None:
            self._pr_extractor_service = PullRequestExtractorService()
        return self._pr_extractor_service
    
    def get_logging_service(self) -> JobLoggingService:
        """Retorna instância do serviço de logging."""
        if self._logging_service is None:
            self._logging_service = JobLoggingService()
        return self._logging_service
    
    def get_response_builder_service(self) -> ResponseBuilderService:
        """Retorna instância do serviço de construção de respostas."""
        if self._response_builder_service is None:
            pr_extractor = self.get_pr_extractor_service()
            logging_service = self.get_logging_service()
            self._response_builder_service = ResponseBuilderService(pr_extractor, logging_service)
        return self._response_builder_service
    
    def get_repository_normalizer_service(self) -> RepositoryNormalizerService:
        """Retorna instância do serviço de normalização de repositórios."""
        if self._repository_normalizer_service is None:
            self._repository_normalizer_service = RepositoryNormalizerService()
        return self._repository_normalizer_service
    
    def get_job_data_service(self) -> JobDataService:
        """Retorna instância do serviço de dados de jobs."""
        if self._job_data_service is None:
            self._job_data_service = JobDataService()
        return self._job_data_service
    
    def get_job_validation_service(self) -> JobValidationService:
        """Retorna instância do serviço de validação de jobs."""
        if self._job_validation_service is None:
            self._job_validation_service = JobValidationService()
        return self._job_validation_service
