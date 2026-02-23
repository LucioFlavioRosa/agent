from azure.storage.blob.aio import BlobServiceClient
from azure.storage.queue.aio import QueueClient

async def create_blob_service_client(connection_string: str) -> BlobServiceClient:
    """
    Instancia um BlobServiceClient de forma assíncrona.
    """
    return BlobServiceClient.from_connection_string(connection_string)

async def create_queue_client(connection_string: str, queue_name: str) -> QueueClient:
    """
    Instancia um QueueClient de forma assíncrona.
    """
    return QueueClient.from_connection_string(conn_str=connection_string, queue_name=queue_name)
