import os
from tools.azure_repository_provider import AzureRepositoryProvider

class AzureConector:
    def __init__(self, organization=None, project=None, pat=None):
        self.organization = organization or os.getenv('AZURE_DEVOPS_ORGANIZATION')
        self.project = project or os.getenv('AZURE_DEVOPS_PROJECT')
        self.pat = pat or os.getenv('AZURE_DEVOPS_PAT')

    @classmethod
    def create_with_defaults(cls):
        return cls()

    def connection(self, repositorio, repository_type=None, repository_provider=None):
        organization = self.organization
        project = self.project
        pat = self.pat
        if not organization or not project or not pat:
            raise Exception(f"[AzureConector] Variáveis de ambiente obrigatórias ausentes. organization={organization}, project={project}, pat={'definido' if pat else 'None'}")
        provider = repository_provider or AzureRepositoryProvider(organization, project, pat)
        repo = provider.get_repository(repositorio)
        # Garantir que os atributos estejam definidos
        if not hasattr(repo, '_organization') or repo._organization is None:
            setattr(repo, '_organization', organization)
        if not hasattr(repo, '_project') or repo._project is None:
            setattr(repo, '_project', project)
        if not hasattr(repo, '_provider_type') or repo._provider_type is None:
            setattr(repo, '_provider_type', 'azure_devops')
        if not hasattr(repo, 'id') or getattr(repo, 'id', None) is None:
            # Tenta obter o id do repositório via provider
            repo_id = getattr(repo, 'id', None)
            if not repo_id:
                try:
                    repo_id = provider.get_repository_id(repositorio)
                    setattr(repo, 'id', repo_id)
                except Exception as e:
                    print(f"[AzureConector] Falha ao obter id do repositório '{repositorio}': {e}")
                    setattr(repo, 'id', None)
        print(f"[AzureConector] Objeto repo criado: type={type(repo)}, _organization={getattr(repo, '_organization', None)}, _project={getattr(repo, '_project', None)}, id={getattr(repo, 'id', None)}, _provider_type={getattr(repo, '_provider_type', None)}")
        return repo
