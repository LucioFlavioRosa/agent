from azure.storage.blob.aio import BlobServiceClient
from typing import Optional

class BlobStorageService:
    @staticmethod
    async def upload_file(blob_conn_str: str, container: str, blob_path: str, content: bytes) -> str:
        async with BlobServiceClient.from_connection_string(blob_conn_str) as blob_service_client:
            container_client = blob_service_client.get_container_client(container)
            if not await container_client.exists():
                await container_client.create_container()
            blob_client = container_client.get_blob_client(blob_path)
            await blob_client.upload_blob(content, overwrite=True)
            return blob_client.url

    @staticmethod
    async def upload_markdown(blob_conn_str: str, container: str, blob_path: str, markdown_content: str) -> str:
        content_bytes = markdown_content.encode('utf-8')
        return await BlobStorageService.upload_file(blob_conn_str, container, blob_path, content_bytes)
