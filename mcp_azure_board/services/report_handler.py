from typing import Dict, Any, Optional

class ReportHandler:
    """
    Handler simplificado para extração de texto de relatórios e salvamento no Blob Storage.
    """
    def __init__(self, blob_storage):
        self.blob_storage = blob_storage

    def extract_report_text(self, step_result: Dict[str, Any]) -> Optional[str]:
        """Extrai o texto do relatório do resultado do step."""
        if not step_result:
            return None
        # Assume que o relatório está em 'resultado' > 'reposta_final' > 'report' ou 'texto'
        resultado = step_result.get('resultado')
        if isinstance(resultado, dict):
            # Busca por chave 'report' ou 'texto' ou 'reposta_final'
            for key in ['report', 'texto', 'reposta_final', 'analysis_report']:
                value = resultado.get(key)
                if value and isinstance(value, str):
                    return value
            # Caso a resposta final seja um dict
            reposta_final = resultado.get('reposta_final')
            if isinstance(reposta_final, dict):
                for key in ['report', 'texto', 'analysis_report']:
                    value = reposta_final.get(key)
                    if value and isinstance(value, str):
                        return value
        # Fallback: se step_result for string
        if isinstance(step_result, str):
            return step_result
        return None

    def save_report_to_blob(self, job_id: str, job_info: Dict[str, Any], report_text: str) -> Optional[str]:
        """Salva o relatório no Blob Storage e retorna a URL."""
        projeto = job_info['data'].get('projeto')
        analysis_type = job_info['data'].get('original_analysis_type')
        repository_type = job_info['data'].get('repository_type')
        repo_name = job_info['data'].get('repo_name')
        branch_name = job_info['data'].get('branch_name_modernizado')
        analysis_name = job_info['data'].get('analysis_name')
        if not all([projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name]):
            raise ValueError("Dados insuficientes para salvar relatório no Blob Storage.")
        url = self.blob_storage.upload_report(
            report_text,
            projeto,
            analysis_type,
            repository_type,
            repo_name,
            branch_name,
            analysis_name
        )
        return url
