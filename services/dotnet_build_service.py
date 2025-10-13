import subprocess
import os
import shutil
from typing import Dict, Any, Optional, List
from tools.azure_secret_manager import AzureSecretManager

class DotNetBuildService:
    def __init__(self):
        self.secret_manager = AzureSecretManager()

    def build_project(self, job_id: str, repository_type: str, repo_name: str, branch_name: str, usuario_executor: Optional[str] = None) -> Dict[str, Any]:
        print(f"[{job_id}] [DotNetBuildService] Iniciando build para repo={repo_name}, branch={branch_name}")
        result = {
            "success": False,
            "errors": [],
            "stdout": "",
            "stderr": ""
        }
        local_dir = f"/tmp/{job_id}_{branch_name}"
        try:
            clone_url = self._get_clone_url(repository_type, repo_name)
            token = self._get_token_for_repository(repository_type, repo_name, usuario_executor)
            if token:
                org = self._extract_org_from_repo_name(repository_type, repo_name)
                print(f"[{job_id}] [DotNetBuildService] Token encontrado para org={org}, repository_type={repository_type}")
                if repository_type == "azure":
                    # Exemplo: https://{token}@dev.azure.com/org/project/repo
                    if clone_url.startswith("https://"):
                        clone_url = clone_url.replace("https://", f"https://{token}@", 1)
                elif repository_type == "github":
                    # Exemplo: https://{token}@github.com/org/repo.git
                    if clone_url.startswith("https://"):
                        clone_url = clone_url.replace("https://", f"https://{token}@", 1)
                elif repository_type == "gitlab":
                    # Exemplo: https://oauth2:{token}@gitlab.com/namespace/repo.git
                    if clone_url.startswith("https://"):
                        clone_url = clone_url.replace("https://", f"https://oauth2:{token}@", 1)
                else:
                    print(f"[{job_id}] [DotNetBuildService] Tipo de repositório não reconhecido para autenticação: {repository_type}")
            else:
                print(f"[{job_id}] [DotNetBuildService] Nenhum token encontrado, tentando clone sem autenticação.")
            if os.path.exists(local_dir):
                shutil.rmtree(local_dir)
            clone_cmd = ["git", "clone", "--branch", branch_name, clone_url, local_dir]
            clone_proc = subprocess.run(clone_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if clone_proc.returncode != 0:
                result["errors"].append(f"Erro ao clonar repositório: {clone_proc.stderr}")
                result["stderr"] = clone_proc.stderr
                print(f"[{job_id}] [DotNetBuildService] Build finalizado. success={result['success']}, errors={len(result['errors'])}")
                return result
            build_cmd = ["dotnet", "build"]
            build_proc = subprocess.run(build_cmd, cwd=local_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            result["stdout"] = build_proc.stdout
            result["stderr"] = build_proc.stderr
            if build_proc.returncode == 0:
                result["success"] = True
            else:
                result["errors"] = self._parse_build_errors(build_proc.stdout, build_proc.stderr)
        except Exception as e:
            result["errors"].append(str(e))
        finally:
            if os.path.exists(local_dir):
                try:
                    shutil.rmtree(local_dir)
                except Exception:
                    pass
        print(f"[{job_id}] [DotNetBuildService] Build finalizado. success={result['success']}, errors={len(result['errors'])}")
        return result

    def _get_clone_url(self, repository_type: str, repo_name: str) -> str:
        if repository_type == "azure":
            return f"https://dev.azure.com/{repo_name}"
        elif repository_type == "github":
            return f"https://github.com/{repo_name}.git"
        elif repository_type == "gitlab":
            return f"https://gitlab.com/{repo_name}.git"
        return repo_name

    def _parse_build_errors(self, stdout: str, stderr: str) -> List[str]:
        errors = []
        for line in (stdout + "\n" + stderr).splitlines():
            if "error" in line.lower():
                errors.append(line.strip())
        return errors if errors else ["Falha no build, mas nenhum erro específico encontrado."]

    def _get_token_for_repository(self, repository_type: str, repo_name: str, usuario_executor: Optional[str]) -> Optional[str]:
        org = self._extract_org_from_repo_name(repository_type, repo_name)
        search_keys = []
        if usuario_executor:
            search_keys.append(f"{repository_type}-token-{org}-{usuario_executor}")
        search_keys.append(f"{repository_type}-token-{org}")
        search_keys.append(f"{repository_type}-token")
        for key in search_keys:
            try:
                token = self.secret_manager.get_secret(key)
                if token:
                    print(f"[DotNetBuildService] Token encontrado para chave: {key}")
                    return token
            except Exception as e:
                print(f"[DotNetBuildService] Erro ao buscar token para chave {key}: {e}")
        print(f"[DotNetBuildService] Nenhum token encontrado para repo_type={repository_type}, org={org}, usuario_executor={usuario_executor}")
        return None

    def _extract_org_from_repo_name(self, repository_type: str, repo_name: str) -> str:
        if repository_type == "azure":
            parts = repo_name.split('/')
            if len(parts) >= 1:
                return parts[0]
            else:
                raise ValueError(f"Nome do repositório Azure inválido: {repo_name}")
        elif repository_type == "github":
            parts = repo_name.split('/')
            if len(parts) >= 1:
                return parts[0]
            else:
                raise ValueError(f"Nome do repositório GitHub inválido: {repo_name}")
        elif repository_type == "gitlab":
            try:
                # Tenta tratar como Project ID numérico
                int(repo_name)
                return 'gitlab'
            except ValueError:
                parts = repo_name.strip().split('/')
                if len(parts) >= 1:
                    return parts[0]
                else:
                    return 'gitlab'
        else:
            raise ValueError(f"Tipo de repositório não suportado para extração de organização: {repository_type}")
