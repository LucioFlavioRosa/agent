import subprocess
import os
import shutil
from typing import Dict, Any, Optional, List
from urllib.parse import quote
from tools.azure_secret_manager import AzureSecretManager

class DotNetBuildService:
    def __init__(self):
        self.secret_manager = AzureSecretManager()

    def build_project(self, job_id: str, repository_type: str, repo_name: str, branch_name: str, git_username: Optional[str] = None, git_token: Optional[str] = None) -> Dict[str, Any]:
        print(f"[{job_id}] [DotNetBuildService] Iniciando build para repo={repo_name}, branch={branch_name}")
        result = {
            "success": False,
            "errors": [],
            "stdout": "",
            "stderr": ""
        }
        local_dir = f"/tmp/{job_id}_{branch_name}"
        try:
            clone_url, used_username, used_token = self._get_clone_url(repository_type, repo_name, git_username, git_token)
            if os.path.exists(local_dir):
                shutil.rmtree(local_dir)
            clone_cmd = ["git", "clone", "--branch", branch_name, clone_url, local_dir]
            try:
                clone_proc = subprocess.run(clone_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            except Exception as e:
                result["errors"].append(f"Erro ao executar git clone: {str(e)}")
                result["stderr"] = str(e)
                print(f"[{job_id}] [DotNetBuildService] Build finalizado. success={result['success']}, errors={len(result['errors'])}")
                return result
            if clone_proc.returncode != 0:
                if used_username or used_token:
                    print(f"[{job_id}] [DotNetBuildService] Falha de autenticação ao clonar repositório privado. Token fornecido: {'sim' if used_token else 'não'} (valor não exibido)")
                    result["errors"].append(f"Erro de autenticação ao clonar repositório: {clone_proc.stderr}")
                else:
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

    def _parse_azure_repo_name(self, repo_name: str):
        parts = repo_name.split('/')
        if len(parts) != 3:
            raise ValueError(f"Nome do repositório Azure '{repo_name}' tem formato inválido. Esperado 'organization/project/repository'.")
        return parts[0], parts[1], parts[2]

    def _get_clone_url(self, repository_type: str, repo_name: str, git_username: Optional[str] = None, git_token: Optional[str] = None):
        used_username = git_username
        used_token = git_token
        if repository_type == "azure":
            try:
                org, project, repo = self._parse_azure_repo_name(repo_name)
            except Exception as e:
                raise ValueError(f"Erro ao parsear repo_name Azure: {e}")
            if not git_username or not git_token:
                try:
                    token = self.secret_manager.get_token(org, "Azure")
                    if token:
                        used_username = "pat"
                        used_token = token
                        print(f"[DotNetBuildService] Token Azure DevOps lido do SecretManager para org '{org}'.")
                except Exception as e:
                    print(f"[DotNetBuildService] Erro ao buscar token do SecretManager para org '{org}': {e}")
            safe_username = quote(used_username, safe='') if used_username else ''
            safe_token = quote(used_token, safe='') if used_token else ''
            if safe_username and safe_token:
                url = f"https://{safe_username}:{safe_token}@dev.azure.com/{org}/{project}/_git/{repo}"
                print(f"[DotNetBuildService] URL de clone Azure DevOps com autenticação construída: https://{safe_username}:***@dev.azure.com/{org}/{project}/_git/{repo}")
            else:
                url = f"https://dev.azure.com/{org}/{project}/_git/{repo}"
                print(f"[DotNetBuildService] URL de clone Azure DevOps sem autenticação construída: {url}")
            return url, used_username, used_token
        if git_username and git_token:
            safe_username = quote(git_username, safe='')
            safe_token = quote(git_token, safe='')
            if repository_type == "github":
                url = f"https://{safe_username}:{safe_token}@github.com/{repo_name}.git"
                print(f"[DotNetBuildService] Clonando repositório privado GitHub com autenticação.")
                return url, git_username, git_token
            elif repository_type == "gitlab":
                url = f"https://{safe_username}:{safe_token}@gitlab.com/{repo_name}.git"
                print(f"[DotNetBuildService] Clonando repositório privado GitLab com autenticação.")
                return url, git_username, git_token
            else:
                url = f"https://{safe_username}:{safe_token}@{repo_name}"
                print(f"[DotNetBuildService] Clonando repositório privado customizado com autenticação.")
                return url, git_username, git_token
        else:
            if repository_type == "github":
                url = f"https://github.com/{repo_name}.git"
                print(f"[DotNetBuildService] Clonando repositório público GitHub.")
                return url, None, None
            elif repository_type == "gitlab":
                url = f"https://gitlab.com/{repo_name}.git"
                print(f"[DotNetBuildService] Clonando repositório público GitLab.")
                return url, None, None
            elif repository_type == "azure":
                # já tratado acima
                pass
            url = repo_name
            print(f"[DotNetBuildService] Clonando repositório customizado sem autenticação.")
            return url, None, None

    def _parse_build_errors(self, stdout: str, stderr: str) -> List[str]:
        errors = []
        for line in (stdout + "\n" + stderr).splitlines():
            if "error" in line.lower():
                errors.append(line.strip())
        return errors if errors else ["Falha no build, mas nenhum erro específico encontrado."]
