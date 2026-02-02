from typing import List, Dict, Any, Optional
import time
from urllib.parse import urlparse
import os
from agents.logging_utils import log_custom_data
from models import JobStatus, JobFields

class JobLoggingService:
    """Serviço responsável por realizar logging estruturado de jobs."""
    def _build_base_log_entry(self, job_id: str, job_data: dict, status: str) -> dict:
        return {
            'job_id': job_id,
            'projeto': job_data.get(JobFields.PROJETO),
            'data_hora': time.strftime('%Y-%m-%d %H:%M:%S'),
            'status': status,
            'tipo_repositorio': job_data.get(JobFields.REPOSITORY_TYPE),
            'nome_repositorio': job_data.get(JobFields.REPO_NAME),
            'tipo_analise': job_data.get(JobFields.ORIGINAL_ANALYSIS_TYPE),
            'branch_name': job_data.get(JobFields.BRANCH_NAME),
            'analysis_name': job_data.get(JobFields.ANALYSIS_NAME),
            'arquivos_especificos': job_data.get(JobFields.ARQUIVOS_ESPECIFICOS),
            'retornar_lista_arquivos': job_data.get(JobFields.RETORNAR_LISTA_ARQUIVOS),
            'modo_adicao_incremental': job_data.get(JobFields.MODO_ADICAO_INCREMENTAL),
            'usuario_executor': job_data.get(JobFields.USUARIO_EXECUTOR)
        }
    def log_completed_job(self, job_id: str, job_data: dict, summary_list: List, blob_url: Optional[str]) -> None:
        blob_filename = self._extract_blob_filename(blob_url)
        base_entry = self._build_base_log_entry(job_id, job_data, JobStatus.COMPLETED)
        base_entry['blob_filename'] = blob_filename
        log_custom_data(**base_entry)
        for pr_summary in summary_list:
            pr_entry = base_entry.copy()
            pr_entry.update({
                'branch_name': job_data.get(JobFields.BRANCH_NAME_MODERNIZADO),
                'pr_url': pr_summary.pull_request_url,
                'arquivos_modificados': pr_summary.arquivos_modificados
            })
            log_custom_data(**pr_entry)
    def log_failed_job(self, job_id: str, job_data: dict, blob_url: Optional[str]) -> None:
        blob_filename = self._extract_blob_filename(blob_url)
        base_entry = self._build_base_log_entry(job_id, job_data, JobStatus.FAILED)
        base_entry['blob_filename'] = blob_filename
        log_custom_data(**base_entry)
    def log_starting_job(self, job_id: str, payload_data: dict, normalized_repo_name: str, analysis_name: str) -> None:
        base_entry = {
            'job_id': job_id,
            'projeto': payload_data.get('projeto'),
            'data_hora': time.strftime('%Y-%m-%d %H:%M:%S'),
            'status': JobStatus.STARTING,
            'tipo_repositorio': payload_data.get('repository_type'),
            'nome_repositorio': normalized_repo_name,
            'tipo_analise': payload_data.get('analysis_type'),
            'branch_name': payload_data.get('branch_name_modernizado'),
            'analysis_name': analysis_name,
            'arquivos_especificos': payload_data.get('arquivos_especificos'),
            'retornar_lista_arquivos': payload_data.get('retornar_lista_arquivos'),
            'modo_adicao_incremental': payload_data.get('modo_adicao_incremental'),
            'usuario_executor': payload_data.get('usuario_executor')
        }
        log_custom_data(**base_entry)
    def _extract_blob_filename(self, blob_url: Optional[str]) -> Optional[str]:
        if not blob_url:
            return None
        try:
            parsed = urlparse(blob_url)
            path = parsed.path
            filename = os.path.basename(path)
            if filename:
                return filename
            else:
                return blob_url
        except Exception:
            try:
                return blob_url.split('/')[-1]
            except Exception:
                return blob_url
