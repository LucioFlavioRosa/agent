from services.response_builder_service import ResponseBuilderService
from services.pull_request_extractor_service import PullRequestExtractorService
from services.job_logging_service import JobLoggingService
from services.repository_normalizer_service import RepositoryNormalizerService
from services.job_data_service import JobDataService
from services.job_validation_service import JobValidationService

class ApiServiceFactory:
    """Factory para criação e configuração de serviços da API. Simplificada para facilitar manutenção."""
    def __init__(self, pr_extractor=None, logging_service=None):
        self.pr_extractor = pr_extractor or PullRequestExtractorService()
        self.logging_service = logging_service or JobLoggingService()
        self.response_builder_service = ResponseBuilderService(self.pr_extractor, self.logging_service)
        self.repository_normalizer_service = RepositoryNormalizerService()
        self.job_data_service = JobDataService()
        self.job_validation_service = JobValidationService()

    def get_pr_extractor_service(self) -> PullRequestExtractorService:
        return self.pr_extractor

    def get_logging_service(self) -> JobLoggingService:
        return self.logging_service

    def get_response_builder_service(self) -> ResponseBuilderService:
        return self.response_builder_service

    def get_repository_normalizer_service(self) -> RepositoryNormalizerService:
        return self.repository_normalizer_service

    def get_job_data_service(self) -> JobDataService:
        return self.job_data_service

    def get_job_validation_service(self) -> JobValidationService:
        return self.job_validation_service
