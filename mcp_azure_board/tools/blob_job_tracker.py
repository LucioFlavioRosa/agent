import os
from azure.storage.blob import BlobServiceClient
import json

class BlobJobTracker:
    @staticmethod
    def build_tracker_blob_path(report_blob_path: str) -> str:
        # Adiciona sufixo para o arquivo de rastreamento de jobs
        return report_blob_path + '.jobs.json'

    @staticmethod
    def append_job_id(blob_service_client: BlobServiceClient, container_name: str, tracker_path: str, job_id: str):
        try:
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=tracker_path)
            job_list = []
            if blob_client.exists():
                raw = blob_client.download_blob().readall().decode('utf-8')
                try:
                    job_list = json.loads(raw)
                    if not isinstance(job_list, list):
                        job_list = []
                except Exception:
                    job_list = []
            if job_id not in job_list:
                job_list.append(job_id)
                blob_client.upload_blob(json.dumps(job_list), overwrite=True)
        except Exception as e:
            print(f"[BlobJobTracker] Warning: Failed to append job_id {job_id} to tracker {tracker_path}: {e}")

    @staticmethod
    def read_job_list(blob_service_client: BlobServiceClient, container_name: str, tracker_path: str):
        try:
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=tracker_path)
            if not blob_client.exists():
                return []
            raw = blob_client.download_blob().readall().decode('utf-8')
            job_list = json.loads(raw)
            if not isinstance(job_list, list):
                return []
            return job_list
        except Exception as e:
            print(f"[BlobJobTracker] Warning: Failed to read job list from tracker {tracker_path}: {e}")
            return []
