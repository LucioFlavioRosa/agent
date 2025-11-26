import os
from azure.storage.blob import BlobServiceClient

class BlobJobTracker:
    @staticmethod
    def build_tracker_blob_path(blob_path: str) -> str:
        return f"{blob_path}.jobs"

    @staticmethod
    def append_job_id(blob_service_client: BlobServiceClient, container_name: str, tracker_path: str, job_id: str):
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=tracker_path)
        job_list = []
        if blob_client.exists():
            job_list = BlobJobTracker.read_job_list(blob_service_client, container_name, tracker_path)
        if job_id not in job_list:
            job_list.append(job_id)
            blob_client.upload_blob("\n".join(job_list), overwrite=True)

    @staticmethod
    def read_job_list(blob_service_client: BlobServiceClient, container_name: str, tracker_path: str):
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=tracker_path)
        if not blob_client.exists():
            return []
        content = blob_client.download_blob().readall().decode('utf-8')
        return [line.strip() for line in content.splitlines() if line.strip()]