import os
from typing import Optional

class AzureConector:
    @staticmethod
    def create_with_defaults():
        return AzureConector()

    def connection(self, organization: Optional[str] = None, project: Optional[str] = None, pat: Optional[str] = None):
        if organization is None:
            organization = os.getenv('AZURE_DEVOPS_ORGANIZATION')
        if project is None:
            project = os.getenv('AZURE_DEVOPS_PROJECT')
        if pat is None:
            pat = os.getenv('AZURE_DEVOPS_PAT')
        if not isinstance(organization, str):
            raise TypeError(f"organization deve ser string, recebido {type(organization)}")
        if not isinstance(project, str):
            raise TypeError(f"project deve ser string, recebido {type(project)}")
        if not pat or not isinstance(pat, str):
            raise Exception(f"[AzureConector] Variáveis de ambiente obrigatórias ausentes ou com tipo incorreto. organization={organization} (tipo: {type(organization)}), project={project} (tipo: {type(project)}), pat={'presente' if pat else 'None'}")
        # ... resto da implementação original ...
        # Aqui deveria seguir a lógica de conexão real ao Azure DevOps
        pass
