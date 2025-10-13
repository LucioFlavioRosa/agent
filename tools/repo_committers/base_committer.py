from typing import List, Dict, Any
from tools.repo_committers.path_validator import PathValidator

class BaseCommitter:
    @staticmethod
    def _inicializar_resultado_branch(nome_branch: str) -> Dict[str, Any]:
        return {
            "branch_name": nome_branch,
            "success": False,
            "pr_url": None,
            "message": None,
            "arquivos_modificados": [],
            "commit_url": None
        }

    @staticmethod
    def _finalizar_resultado_sucesso(resultado_branch: Dict[str, Any], pr_url: str = None, message: str = None):
        resultado_branch["success"] = True
        if pr_url:
            resultado_branch["pr_url"] = pr_url
        if message:
            resultado_branch["message"] = message
        return resultado_branch

    @staticmethod
    def _finalizar_resultado_erro(resultado_branch: Dict[str, Any], message: str):
        resultado_branch["success"] = False
        resultado_branch["message"] = message
        return resultado_branch

    @staticmethod
    def _validate_no_duplicate_paths(conjunto_de_mudancas: List[Dict[str, Any]]):
        paths = set()
        for idx, mudanca in enumerate(conjunto_de_mudancas):
            caminho = mudanca.get("caminho")
            try:
                caminho_validado = PathValidator.validate_path(caminho)
            except Exception as e:
                print(f"[ERRO][BaseCommitter][_validate_no_duplicate_paths] Mudança {idx}: caminho inválido: '{caminho}'. Erro: {e}")
                raise ValueError(f"Mudança {idx}: caminho inválido: '{caminho}'. Erro: {e}")
            if caminho_validado in paths:
                print(f"[ERRO][BaseCommitter][_validate_no_duplicate_paths] Caminho duplicado detectado: '{caminho_validado}' (mudança {idx})")
                raise ValueError(f"Arquivo duplicado na lista de mudanças: {caminho_validado}")
            print(f"[DEBUG][BaseCommitter][_validate_no_duplicate_paths] Caminho validado: '{caminho_validado}' (mudança {idx})")
            paths.add(caminho_validado)
        print(f"[DEBUG][BaseCommitter][_validate_no_duplicate_paths] Total de caminhos validados: {len(paths)}")

    @staticmethod
    def _validate_commit_url(url: str) -> bool:
        if not url or not isinstance(url, str):
            return False
        return url.startswith('http://') or url.startswith('https://') or "Branch processada" in url or "PR criado" in url or "MR criado" in url

    @staticmethod
    def _mesclar_conteudo(conteudo_existente: str, conteudo_novo: str) -> str:
        if conteudo_existente is None:
            return conteudo_novo or ""
        if conteudo_novo is None:
            return conteudo_existente or ""
        return conteudo_existente + "\n" + conteudo_novo

    @staticmethod
    def _processar_mudancas_comuns(conjunto_de_mudancas: List[Dict[str, Any]], resultado_branch: Dict[str, Any]) -> List[Dict[str, Any]]:
        mudancas_validas = []
        ignoradas = 0
        for idx, mudanca in enumerate(conjunto_de_mudancas):
            status = mudanca.get("status")
            caminho = mudanca.get("caminho")
            conteudo = mudanca.get("conteudo")
            try:
                caminho_validado = PathValidator.validate_path(caminho)
            except Exception as e:
                print(f"[ERRO][BaseCommitter][_processar_mudancas_comuns] Mudança {idx}: caminho inválido: '{caminho}', status='{status}', conteudo='{str(conteudo)[:100]}'. Erro: {e}")
                ignoradas += 1
                continue
            if status in ("ADICIONADO", "CRIADO", "MODIFICADO"):
                if conteudo is None or (isinstance(conteudo, str) and conteudo.strip() == ""):
                    print(f"[ERRO][BaseCommitter] Mudança ignorada: arquivo '{caminho_validado}' com status '{status}' possui conteudo vazio ou None.")
                    ignoradas += 1
                    continue
            mudancas_validas.append({**mudanca, "caminho": caminho_validado})
            print(f"[DEBUG][BaseCommitter][_processar_mudancas_comuns] Mudança {idx}: caminho validado '{caminho_validado}'")
        print(f"[DEBUG][BaseCommitter][_processar_mudancas_comuns] Total processadas: {len(conjunto_de_mudancas)}, válidas: {len(mudancas_validas)}, ignoradas: {ignoradas}")
        return mudancas_validas

    @staticmethod
    def _validate_branch_exists(repo, branch_name, repository_type, branch_de_origem=None):
        if repository_type == 'github':
            from github import GithubException
            try:
                repo.get_branch(branch_name)
                print(f"[DEBUG][BaseCommitter] Branch '{branch_name}' já existe no GitHub.")
                return True
            except GithubException as e:
                if e.status == 404:
                    print(f"[DEBUG][BaseCommitter] Branch '{branch_name}' não existe no GitHub. Tentando criar a partir de '{branch_de_origem}'...")
                    try:
                        sha_origem = repo.get_branch(branch_de_origem).commit.sha
                        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=sha_origem)
                        print(f"[DEBUG][BaseCommitter] Branch '{branch_name}' criada com sucesso a partir de '{branch_de_origem}'.")
                        return True
                    except Exception as err:
                        print(f"[ERRO][BaseCommitter] Falha ao criar branch '{branch_name}' a partir de '{branch_de_origem}': {err}")
                        raise Exception(f"Falha ao criar branch '{branch_name}' a partir de '{branch_de_origem}': {err}")
                else:
                    print(f"[ERRO][BaseCommitter] Erro inesperado ao verificar branch '{branch_name}': {e}")
                    raise
        elif repository_type == 'gitlab':
            try:
                branches = repo.branches.list(search=branch_name)
                if any(b.name == branch_name for b in branches):
                    print(f"[DEBUG][BaseCommitter] Branch '{branch_name}' já existe no GitLab.")
                    return True
                print(f"[DEBUG][BaseCommitter] Branch '{branch_name}' não existe no GitLab. Tentando criar a partir de '{branch_de_origem}'...")
                repo.branches.create({'branch': branch_name, 'ref': branch_de_origem})
                print(f"[DEBUG][BaseCommitter] Branch '{branch_name}' criada com sucesso a partir de '{branch_de_origem}'.")
                return True
            except Exception as err:
                print(f"[ERRO][BaseCommitter] Falha ao criar branch '{branch_name}' no GitLab: {err}")
                raise Exception(f"Falha ao criar branch '{branch_name}' no GitLab: {err}")
        elif repository_type == 'azure':
            # No Azure, a lógica está implementada diretamente no committer devido à API REST
            return True
        else:
            raise Exception(f"[BaseCommitter] Provedor de repositório '{repository_type}' não suportado para validação de branch.")
