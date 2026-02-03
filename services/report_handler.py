import json
import re

class ReportHandler:
    def __init__(self, blob_storage, cache_service=None, user_email=None):
        self.blob_storage = blob_storage
        self.cache_service = cache_service
        self.user_email = user_email

    def read_existing_report_from_blob(self, job_id, job_info, current_step_index):
        projeto = job_info['data'].get('projeto')
        analysis_type = job_info['data'].get('original_analysis_type')
        repository_type = job_info['data'].get('repository_type')
        repo_name = job_info['data'].get('repo_name')
        branch_name = job_info['data'].get('branch_name_modernizado')
        analysis_name = job_info['data'].get('analysis_name')
        user_email = job_info['data'].get('usuario_executor') or self.user_email
        try:
            from tools.blob_report_reader import read_report_from_blob
            report_text = read_report_from_blob(
                projeto=projeto,
                analysis_type=analysis_type,
                repository_type=repository_type,
                repo_name=repo_name,
                branch_name=branch_name,
                analysis_name=analysis_name,
                user_email=user_email
            )
            return report_text
        except Exception as e:
            print(f"[ReportHandler] Erro ao tentar ler relatório do Blob Storage: {e}")
            return None

    def extract_report_text(self, step_result):
        if not step_result:
            return None

        raw_output_str = None

        if isinstance(step_result, dict):
            if 'relatorio' in step_result:
                return step_result['relatorio']
            if 'resultado_gerado' in step_result:
                raw_output_str = step_result['resultado_gerado']
            elif 'resultado' in step_result and isinstance(step_result['resultado'], dict):
                if 'relatorio' in step_result['resultado']:
                    return step_result['resultado']['relatorio']
            elif isinstance(step_result.get('resultado'), str):
                raw_output_str = step_result.get('resultado')
        elif isinstance(step_result, str):
            raw_output_str = step_result

        if not raw_output_str:
            print("[ReportHandler] extract_report_text: step_result não continha uma string de saída reconhecida.")
            return None

        try:
            match = re.search(r'\{.*\}', raw_output_str, re.DOTALL)
            if match:
                json_str = match.group(0)
            else:
                if raw_output_str.strip().startswith('|'):
                    return raw_output_str
                print(f"[ReportHandler] extract_report_text: Não foi possível encontrar um JSON na string: {raw_output_str[:200]}")
                return None
            data = json.loads(json_str)
            if isinstance(data, dict) and 'relatorio' in data:
                return data['relatorio']
            else:
                print(f"[ReportHandler] extract_report_text: JSON parseado não contém a chave 'relatorio'.")
                return None
        except json.JSONDecodeError as e:
            print(f"[ReportHandler] extract_report_text: Falha ao decodificar JSON. Error: {e}. String: {raw_output_str[:200]}")
            if raw_output_str.strip().startswith('|'):
                return raw_output_str
            return None

    def save_report_to_blob(self, job_id, job_info, report_text):
        if not report_text or len(str(report_text).strip()) == 0:
            raise ValueError(f"[{job_id}] ERRO: Tentativa de salvar relatório vazio no Blob Storage.")
        projeto = job_info['data'].get('projeto')
        analysis_type = job_info['data'].get('original_analysis_type')
        repository_type = job_info['data'].get('repository_type')
        repo_name = job_info['data'].get('repo_name')
        branch_name = job_info['data'].get('branch_name_modernizado')
        analysis_name = job_info['data'].get('analysis_name')
        user_email = job_info['data'].get('usuario_executor') or self.user_email
        print(f"[{job_id}] [DEBUG] Iniciando upload do relatório para o Blob Storage...")
        from tools.blob_report_uploader import upload_report_to_blob
        url = upload_report_to_blob(report_text, projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name, user_email)
        if not url:
            raise ValueError(f"[{job_id}] ERRO: Blob Storage não retornou URL válida")
        job_info['data']['report_blob_url'] = url
        job_info['data']['analysis_report'] = report_text
        print(f"[{job_id}] Relatório salvo no Blob Storage: {url} (tamanho: {len(report_text)} chars)")
        try:
            self.blob_storage.update_job_tracker(url, job_id)
        except Exception as e:
            print(f"[ReportHandler] Warning: Failed to update job tracker after saving report: {e}")
        print(f"[{job_id}] [DEBUG] Upload do relatório concluído com sucesso.")
        return url

    def handle_report_only_mode(self, job_id, job_info, step_result):
        report_text = self.extract_report_text(step_result)
        if not report_text or len(report_text.strip()) == 0:
            raise ValueError(f"[{job_id}] ERRO: Tentativa de salvar relatório vazio no modo report_only")
        job_info['data']['analysis_report'] = report_text
        url = self.save_report_to_blob(job_id, job_info, report_text)
        print(f"[{job_id}] Modo report_only: Relatório salvo com sucesso ({len(report_text)} chars)")
        return url

    def validate_and_parse_blob_report(self, report_text, job_id):
        if not report_text or not isinstance(report_text, str):
            print(f"[{job_id}] ERRO: Relatório lido do Blob é inválido. Tipo: {type(report_text)}")
            return None
        if len(report_text.strip()) == 0:
            print(f"[{job_id}] ERRO: Relatório lido do Blob está vazio.")
            return None
        print(f"[{job_id}] Relatório válido lido do Blob Storage ({len(report_text)} chars).")
        return report_text

    def save_report_to_cache(self, cache_key: str, report_text: str):
        if self.cache_service:
            try:
                self.cache_service.set(cache_key, report_text)
            except Exception as e:
                print(f"[ReportHandler] Warning: Failed to save report to cache: {e}")

    def read_report_from_cache(self, cache_key: str):
        if self.cache_service:
            try:
                report = self.cache_service.get(cache_key)
                if report:
                    return report
            except Exception as e:
                print(f"[ReportHandler] Warning: Failed to read report from cache: {e}")
        return None
