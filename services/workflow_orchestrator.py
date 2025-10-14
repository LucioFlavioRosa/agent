import logging

class WorkflowOrchestrator:
    def __init__(self, committer):
        self.committer = committer

    def process_commit_result(self, commit_result):
        branch_name = None
        if 'branch_name' in commit_result:
            branch_name = commit_result['branch_name']
        elif 'branch' in commit_result:
            logging.warning("[orchestrator] Resultado do committer contém a chave 'branch' (formato antigo). Recomenda-se usar 'branch_name'.")
            branch_name = commit_result['branch']
        else:
            raise ValueError("[orchestrator] Resultado do committer não contém a chave obrigatória 'branch_name' nem 'branch'.")
        # ... restante da lógica usando branch_name ...
        return branch_name
