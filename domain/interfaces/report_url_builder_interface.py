from abc import ABC, abstractmethod

class IReportUrlBuilder(ABC):
    @abstractmethod
    def build_report_blob_path(self, projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name) -> str:
        pass

    @abstractmethod
    def build_full_url(self, blob_path: str) -> str:
        pass
