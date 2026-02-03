from tools.readers.base_reader import BaseReader

class BaseFileReader(BaseReader):
    def __init__(self, repository_provider, user_email=None, group_resolver=None):
        super().__init__(repository_provider)
        self.user_email = user_email
        self.group_resolver = group_resolver

    def _read_file_with_error_handling(self, file_getter, file_path, branch_name, repo_name_desc):
        try:
            file_content = file_getter(file_path=file_path, ref=branch_name)
            import base64
            decoded = base64.b64decode(file_content.content).decode('utf-8')
            return decoded
        except Exception as e:
            msg = str(e).lower()
            if "404" in msg or "not found" in msg:
                print(f"[BaseFileReader] AVISO: Arquivo '{file_path}' não encontrado na branch '{branch_name}' do repositório '{repo_name_desc}'.")
                return None
            elif "403" in msg or "forbidden" in msg:
                print(f"[BaseFileReader] AVISO: Sem permissão para acessar o arquivo '{file_path}' na branch '{branch_name}' do repositório '{repo_name_desc}'.")
                raise PermissionError(f"Sem permissão para acessar o arquivo '{file_path}' na branch '{branch_name}'.") from e
            else:
                print(f"[BaseFileReader] ERRO inesperado ao ler arquivo '{file_path}' na branch '{branch_name}' do repositório '{repo_name_desc}': {e}")
                raise RuntimeError(f"Erro inesperado ao ler arquivo '{file_path}' na branch '{branch_name}': {e}") from e
