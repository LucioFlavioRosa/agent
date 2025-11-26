import threading

class AnalysisNameService:
    """
    Serviço para registrar e recuperar nomes de análise e seus respectivos job_ids.
    """
    def __init__(self):
        self._analysis_name_to_job_id = {}
        self._lock = threading.Lock()

    def register_analysis(self, analysis_name: str, job_id: str) -> None:
        """Registra um nome de análise associado a um job_id."""
        with self._lock:
            self._analysis_name_to_job_id[analysis_name] = job_id

    def get_job_id_by_analysis_name(self, analysis_name: str) -> str:
        """Recupera o job_id associado ao nome da análise."""
        with self._lock:
            return self._analysis_name_to_job_id.get(analysis_name)

    def clear(self):
        """Limpa o registro de análises."""
        with self._lock:
            self._analysis_name_to_job_id.clear()
