import os
from azure.storage.blob import BlobServiceClient, ContentSettings
from tools.azure_secret_manager import AzureSecretManager, VaultType
from tools.blob_report_path_builder import build_report_blob_path
from tools.blob_storage_utils import get_blob_connection_string
from tools.user_email_parser import UserEmailParser

def upload_report_to_blob(report_text: str, projeto: str, analysis_type: str, repository_type: str, repo_name: str, branch_name: str, analysis_name: str, user_email: str, group_resolver: object = None) -> str:
    # Resolve grupo e empresa
    if group_resolver is not None:
        grupo = group_resolver.get_group_for_user(user_email)
        _, empresa = UserEmailParser.parse_email(user_email)
    else:
        usuario, empresa = UserEmailParser.parse_email(user_email)
        grupo = usuario
    container_name = f"azure-storage-container-name-{grupo}-{empresa}"
    # Instancia o AzureSecretManager com VaultType.AZURE_INFRASTRUCTURE para ler secrets de infraestrutura
    secret_manager = AzureSecretManager(vault_type=VaultType.AZURE_INFRASTRUCTURE)
    # Nome fixo do secret da connection string
    connection_string = secret_manager.get_secret("azure-storage-connection-string")
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    original_analysis_name = analysis_name
    counter = 1
    while True:
        blob_path = build_report_blob_path(projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_path)
        try:
            if blob_client.exists():
                analysis_name = f"{original_analysis_name}-{counter}"
                counter += 1
                continue
            else:
                break
        except Exception:
            break
    blob_client.upload_blob(report_text, overwrite=True, content_settings=ContentSettings(content_type='text/markdown'))
    return blob_client.url
