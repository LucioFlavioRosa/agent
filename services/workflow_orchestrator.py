import os
import hmac
import hashlib
import yaml

WORKFLOW_FILE = 'workflows.yaml'
HMAC_SECRET = os.getenv('WORKFLOW_HMAC_SECRET', 'default_secret')

class WorkflowOrchestrator:
    def __init__(self):
        self.workflow = None

    def _calculate_file_hmac(self, file_path):
        with open(file_path, 'rb') as f:
            content = f.read()
        return hmac.new(HMAC_SECRET.encode(), content, hashlib.sha256).hexdigest()

    def _validate_workflow_integrity(self, file_path, expected_hmac):
        actual_hmac = self._calculate_file_hmac(file_path)
        if not hmac.compare_digest(actual_hmac, expected_hmac):
            raise RuntimeError(f'Integridade do workflow comprometida: HMAC inválido para {file_path}')

    def load_workflow(self, expected_hmac):
        # Restringe permissões de escrita
        st = os.stat(WORKFLOW_FILE)
        if st.st_mode & 0o002:
            raise PermissionError(f'Permissão de escrita pública detectada em {WORKFLOW_FILE}. Corrija para 640 ou menos.')
        self._validate_workflow_integrity(WORKFLOW_FILE, expected_hmac)
        with open(WORKFLOW_FILE, 'r') as f:
            self.workflow = yaml.safe_load(f)
        return self.workflow

    def execute_workflow(self, job_id, start_from_step=0):
        # Execução isolada (sandbox) pode ser implementada com containers/docker se workflow externo
        # Aqui apenas simulação: não executa código arbitrário, apenas passos validados
        if not self.workflow:
            raise RuntimeError('Workflow não carregado.')
        # ... lógica de execução dos passos do workflow ...
