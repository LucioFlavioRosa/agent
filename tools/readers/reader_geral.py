from tools.conectores.conexao_geral import ConexaoGeral

class ReaderGeral:
    def __init__(self, repository_provider=None):
        self.repository_provider = repository_provider
    def read_repository(self, nome_repo, tipo_analise, repository_type, nome_branch=None, arquivos_especificos=None, retornar_lista_arquivos=False):
        if repository_type == 'azure':
            try:
                parts = nome_repo.split('/')
                if len(parts) != 3:
                    raise ValueError(f"nome_repo para Azure deve estar no formato organization/project/repository. Recebido: {nome_repo}")
                organization, project, repository = parts
                pat = None
                from os import getenv
                pat = getenv('AZURE_DEVOPS_PAT')
                print(f"[DEBUG][reader_geral] Chamando connection com organization={organization} (tipo: {type(organization)}), project={project} (tipo: {type(project)}), pat={'presente' if pat else 'ausente'}")
                conexao_geral = ConexaoGeral.create_with_defaults()
                repo_obj = conexao_geral.connection(organization=organization, project=project, pat=pat)
                # ... lógica para ler o repositório ...
                # Retornar o resultado esperado
                return {}
            except Exception as e:
                print(f"[ERRO][reader_geral] Falha ao conectar ao Azure DevOps: {e}")
                raise
        # ... restante do método para outros tipos de repositório ...
        pass
