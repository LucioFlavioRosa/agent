import os

class BlobUrlBuilder:
    def build_report_blob_path(self, projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name):
        from tools.blob_report_path_builder import build_report_blob_path
        return build_report_blob_path(projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name)

    def build_full_url(self, blob_path):
        container_name = os.getenv('AZURE_STORAGE_CONTAINER_NAME')
        account_url = os.getenv('AZURE_STORAGE_ACCOUNT_URL')
        if account_url and container_name:
            return f"{account_url}/{container_name}/{blob_path}"
        elif container_name:
            return f"/{container_name}/{blob_path}"
        else:
            return blob_path
