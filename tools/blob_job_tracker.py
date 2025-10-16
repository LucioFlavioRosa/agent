import os
from typing import List
from azure.storage.blob import ContentSettings

class BlobJobTracker:
    @staticmethod
    def build_tracker_blob_path(report_blob_path: str) -> str:
        # Adiciona o sufixo _id_job.md ao nome do arquivo de relatório
        if report_blob_path.endswith('.md'):
            return report_blob_path[:-3] + '_id_job.md'
        else:
            return report_blob_path + '_id_job.md'

    @staticmethod
    def read_job_list(blob_service_client, container_name: str, tracker_path: str) -> List[str]:
        try:
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=tracker_path)
            if not blob_client.exists():
                return []
            content = blob_client.download_blob().readall().decode('utf-8')
            lines = content.splitlines()
            job_ids = []
            for line in lines:
                line = line.strip()
                if line.startswith('- '):
                    job_id = line[2:].strip()
                    if job_id:
                        job_ids.append(job_id)
            return job_ids
        except Exception as e:
            print(f"[BlobJobTracker] Warning: Failed to read job list from {tracker_path}: {e}")
            return []

    @staticmethod
    def append_job_id(blob_service_client, container_name: str, tracker_path: str, job_id: str) -> None:
        try:
            job_ids = BlobJobTracker.read_job_list(blob_service_client, container_name, tracker_path)
            if job_id in job_ids:
                return
            job_ids.append(job_id)
            content = BlobJobTracker.format_tracker_content(job_ids)
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=tracker_path)
            blob_client.upload_blob(content, overwrite=True, content_settings=ContentSettings(content_type='text/markdown'))
        except Exception as e:
            print(f"[BlobJobTracker] Warning: Failed to append job_id to {tracker_path}: {e}")

    @staticmethod
    def format_tracker_content(job_ids: List[str]) -> str:
        lines = ['# Job IDs que utilizaram este relatório', '']
        for job_id in job_ids:
            lines.append(f'- {job_id}')
        return '\n'.join(lines) + '\n'
