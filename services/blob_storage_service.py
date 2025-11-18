from azure.storage.blob import BlobServiceClient
import os

class BlobStorageService:
    def __init__(self):
        account_url = os.getenv('AZURE_STORAGE_ACCOUNT_URL')
        credential = os.getenv('AZURE_STORAGE_KEY')
        # Garante uso de HTTPS
        if not account_url or not account_url.startswith('https://'):
            raise ValueError('A URL da conta do Azure Blob Storage deve usar HTTPS.')
        self.client = BlobServiceClient(account_url=account_url, credential=credential)

    def upload_report(self, container_name, blob_name, data):
        container_client = self.client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(data, overwrite=True)

    def download_report(self, container_name, blob_name):
        container_client = self.client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        stream = blob_client.download_blob()
        return stream.readall()
