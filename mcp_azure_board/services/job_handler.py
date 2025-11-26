from typing import Dict, Any, Optional

class JobHandler:
    """
    Serviço auxiliar para manipulação de jobs: leitura, atualização, resultados de steps, etc.
    """
    def __init__(self, job_store):
        self.job_store = job_store

    def get_job_info(self, job_id: str) -> Dict[str, Any]:
        """Recupera as informações completas do job."""
        return self.job_store.get_job(job_id)

    def update_job(self, job_id: str, job_info: Dict[str, Any]) -> None:
        """Atualiza as informações do job."""
        self.job_store.set_job(job_id, job_info)

    def update_job_status(self, job_id: str, status: str) -> None:
        """Atualiza o status do job."""
        job_info = self.get_job_info(job_id)
        if job_info:
            job_info['status'] = status
            self.update_job(job_id, job_info)

    def get_step_result(self, job_info: Dict[str, Any], step_index: int) -> Optional[Dict[str, Any]]:
        """Obtém o resultado do step anterior, se existir."""
        steps_results = job_info.get('data', {}).get('steps_results', [])
        if step_index > 0 and step_index - 1 < len(steps_results):
            return steps_results[step_index - 1]
        return None

    def set_paused_step(self, job_info: Dict[str, Any], step_index: int) -> None:
        """Marca o step onde o workflow foi pausado para aprovação."""
        job_info['data']['paused_at_step'] = step_index
