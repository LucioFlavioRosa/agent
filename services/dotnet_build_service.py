import subprocess
import os
import shutil
from typing import Dict, Any, Optional, List
from urllib.parse import quote

class DotNetBuildService:
    def __init__(self):
        pass

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
            clone_url = self._get_clone_url(repository_type, repo_name, git_username, git_token)
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
                if git_username or git_token:
                    print(f"[{job_id}] [DotNetBuildService] Falha de autenticação ao clonar repositório privado.")
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

    def _get_clone_url(self, repository_type: str, repo_name: str, git_username: Optional[str] = None, git_token: Optional[str] = None) -> str:
        if git_username and git_token:
            safe_username = quote(git_username, safe='')
            safe_token = quote(git_token, safe='')
            if repository_type == "azure":
                # Azure DevOps: https://{username}:{token}@dev.azure.com/{org}/{project}/_git/{repo}
                if repo_name.count('/') == 2:
                    org, project, repo = repo_name.split('/')
                    url = f"https://{safe_username}:{safe_token}@dev.azure.com/{org}/{project}/_git/{repo}"
                else:
                    url = f"https://{safe_username}:{safe_token}@dev.azure.com/{repo_name}"
                print(f"[DotNetBuildService] Clonando repositório privado Azure com autenticação.")
                return url
            elif repository_type == "github":
                url = f"https://{safe_username}:{safe_token}@github.com/{repo_name}.git"
                print(f"[DotNetBuildService] Clonando repositório privado GitHub com autenticação.")
                return url
            elif repository_type == "gitlab":
                url = f"https://{safe_username}:{safe_token}@gitlab.com/{repo_name}.git"
                print(f"[DotNetBuildService] Clonando repositório privado GitLab com autenticação.")
                return url
            else:
                url = f"https://{safe_username}:{safe_token}@{repo_name}"
                print(f"[DotNetBuildService] Clonando repositório privado customizado com autenticação.")
                return url
        else:
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
