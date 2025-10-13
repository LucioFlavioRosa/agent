import subprocess
import os
import shutil
from typing import Dict, Any, Optional, List
from urllib.parse import quote
from tools.azure_secret_manager import AzureSecretManager

class DotNetBuildService:
    def __init__(self):
        self.secret_manager = AzureSecretManager()

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
            print(f"[{job_id}] [DotNetBuildService] build_project: repository_type={repository_type}, repo_name={repo_name}, branch_name={branch_name}")
            clone_url, used_username, used_token, auth_method = self._get_clone_url(repository_type, repo_name, job_id)
            print(f"[{job_id}] [DotNetBuildService] URL de clone construída (autenticação: {auth_method}): {clone_url.split('@')[0] + '@***' + clone_url.split('@')[-1] if '@' in clone_url else clone_url}")
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

    def _get_azure_credentials(self, org: str, job_id: Optional[str] = None) -> (Optional[str], Optional[str], str, str):
        secret_name = f"{org}-Azure-PAT"
        token = None
        used_username = None
        used_token = None
        auth_method = ""
        print(f"[{job_id}] [DotNetBuildService] Tentando obter token do SecretManager para org '{org}' (secret: {secret_name})")
        try:
            token = self.secret_manager.get_secret(secret_name)
            if token:
                used_username = "pat"
                used_token = token
                auth_method = f"SecretManager:{secret_name}"
                print(f"[{job_id}] [DotNetBuildService] Token Azure DevOps lido do SecretManager para org '{org}' (secret: {secret_name}).")
            else:
                print(f"[{job_id}] [DotNetBuildService] Nenhum token retornado do SecretManager para org '{org}' (secret: {secret_name}).")
        except Exception as e:
            print(f"[{job_id}] [DotNetBuildService] Erro ao buscar token do SecretManager para org '{org}' (secret: {secret_name}): {e}")
        return used_username, used_token, auth_method, secret_name

    def _get_clone_url(self, repository_type: str, repo_name: str, job_id: Optional[str] = None):
        used_username = None
        used_token = None
        auth_method = ""
        secret_name = ""
        if repository_type == "azure":
            try:
                org, project, repo = self._parse_azure_repo_name(repo_name)
            except Exception as e:
                raise ValueError(f"Erro ao parsear repo_name Azure: {e}")
            used_username, used_token, auth_method, secret_name = self._get_azure_credentials(org, job_id)
            safe_username = quote(used_username, safe='') if used_username else ''
            safe_token = quote(used_token, safe='') if used_token else ''
            if safe_username and safe_token:
                url = f"https://{safe_username}:{safe_token}@dev.azure.com/{org}/{project}/_git/{repo}"
                print(f"[{job_id}] [DotNetBuildService] URL de clone Azure DevOps com autenticação construída: https://{safe_username}:***@dev.azure.com/{org}/{project}/_git/{repo}")
            else:
                url = f"https://dev.azure.com/{org}/{project}/_git/{repo}"
                print(f"[{job_id}] [DotNetBuildService] URL de clone Azure DevOps sem autenticação construída: {url}")
            if not safe_username or not safe_token:
                error_msg = f"Falha ao obter credenciais. git_username/git_token não fornecidos E secret '{secret_name}' não encontrado no SecretManager."
                print(f"[{job_id}] [DotNetBuildService] {error_msg}")
            return url, used_username, used_token, auth_method or "none"
        else:
            url = repo_name
            auth_method = "public"
            print(f"[{job_id}] [DotNetBuildService] Clonando repositório customizado sem autenticação.")
            return url, None, None, auth_method

    def _parse_build_errors(self, stdout: str, stderr: str) -> List[str]:
        errors = []
        for line in (stdout + "\n" + stderr).splitlines():
            if "error" in line.lower():
                errors.append(line.strip())
        return errors if errors else ["Falha no build, mas nenhum erro específico encontrado."]
