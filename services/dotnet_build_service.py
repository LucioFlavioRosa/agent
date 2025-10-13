import subprocess
import os
import shutil
from typing import Dict, Any, Optional, List
from tools.azure_secret_manager import AzureSecretManager
import getpass

class DotNetBuildService:
    def __init__(self):
        pass

    def build_project(self, job_id: str, repository_type: str, repo_name: str, branch_name: str) -> Dict[str, Any]:
        print(f"[{job_id}] [DotNetBuildService] Iniciando build para repo={repo_name}, branch={branch_name}")
        result = {
            "success": False,
            "errors": [],
            "stdout": "",
            "stderr": ""
        }
        local_dir = f"/tmp/{job_id}_{branch_name}"
        try:
            token = self._get_token_for_repository(repository_type, repo_name)
            clone_url = self._build_authenticated_clone_url(repository_type, repo_name, token)
            if token:
                print(f"[{job_id}] [DotNetBuildService] Token encontrado para clone: usando URL autenticada.")
            else:
                print(f"[{job_id}] [DotNetBuildService] Nenhum token encontrado, tentando clone sem autenticação.")
            print(f"[{job_id}] [DotNetBuildService] URL de clone utilizada: {clone_url}")
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

    def _get_token_for_repository(self, repository_type: str, repo_name: str) -> Optional[str]:
        secret_manager = AzureSecretManager()
        usuario = getpass.getuser()
        org = self._extract_org_name(repository_type, repo_name)
        search_keys = []
        if org and usuario:
            search_keys.append(f"{repository_type}-token-{org}-{usuario}")
        if org:
            search_keys.append(f"{repository_type}-token-{org}")
        search_keys.append(f"{repository_type}-token")
        for key in search_keys:
            try:
                token = secret_manager.get_secret(key)
                if token:
                    print(f"[DotNetBuildService] Token encontrado usando chave: {key}")
                    return token
            except Exception as e:
                print(f"[DotNetBuildService] Falha ao buscar token com chave {key}: {e}")
        print(f"[DotNetBuildService] Nenhum token encontrado nas chaves: {search_keys}")
        return None

    def _extract_org_name(self, repository_type: str, repo_name: str) -> Optional[str]:
        if repository_type == "azure":
            parts = repo_name.split('/')
            if len(parts) == 3:
                return parts[0]
        elif repository_type == "github":
            parts = repo_name.split('/')
            if len(parts) >= 2:
                return parts[0]
        elif repository_type == "gitlab":
            if repo_name.isdigit():
                return "gitlab"
            parts = repo_name.split('/')
            if len(parts) >= 2:
                return parts[0]
        return None

    def _build_authenticated_clone_url(self, repository_type: str, repo_name: str, token: Optional[str]) -> str:
        if repository_type == "azure":
            base_url = f"https://dev.azure.com/{repo_name}"
            if token:
                return f"https://{token}@dev.azure.com/{repo_name}"
            else:
                return base_url
        elif repository_type == "github":
            base_url = f"https://github.com/{repo_name}.git"
            if token:
                return f"https://{token}@github.com/{repo_name}.git"
            else:
                return base_url
        elif repository_type == "gitlab":
            if repo_name.isdigit():
                base_url = f"https://gitlab.com/{repo_name}.git"
                if token:
                    return f"https://oauth2:{token}@gitlab.com/{repo_name}.git"
                else:
                    return base_url
            else:
                base_url = f"https://gitlab.com/{repo_name}.git"
                if token:
                    return f"https://oauth2:{token}@gitlab.com/{repo_name}.git"
                else:
                    return base_url
        return repo_name

    def _parse_build_errors(self, stdout: str, stderr: str) -> List[str]:
        errors = []
        for line in (stdout + "\n" + stderr).splitlines():
            if "error" in line.lower():
                errors.append(line.strip())
        return errors if errors else ["Falha no build, mas nenhum erro específico encontrado."]
