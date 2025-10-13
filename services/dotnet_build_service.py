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
            base_clone_url = self._get_clone_url(repository_type, repo_name)
            print(f"[{job_id}] [DotNetBuildService] URL base de clone construída: {base_clone_url}")
            token = self._get_token_for_repository(repository_type, repo_name, usuario_executor)
            print(f"[{job_id}] [DotNetBuildService] Token {'encontrado' if token else 'NÃO encontrado'} para autenticação")
            if token:
                clone_url = self._inject_token_into_url(base_clone_url, token, repository_type)
                masked_clone_url = self._mask_token_in_url(clone_url)
                print(f"[{job_id}] [DotNetBuildService] URL final de clone (token mascarado): {masked_clone_url}")
            else:
                print(f"[{job_id}] [DotNetBuildService] Token não encontrado. Clone de repositório privado pode falhar.")
                clone_url = base_clone_url
                masked_clone_url = clone_url
            if os.path.exists(local_dir):
                shutil.rmtree(local_dir)
            clone_cmd = ["git", "clone", "--branch", branch_name, clone_url, local_dir]
            print(f"[{job_id}] [DotNetBuildService] Comando git clone (token mascarado): {['git', 'clone', '--branch', branch_name, masked_clone_url, local_dir]}")
            clone_proc = subprocess.run(clone_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            print(f"[{job_id}] [DotNetBuildService] git clone retornou código: {clone_proc.returncode}")
            if clone_proc.returncode != 0:
                error_msg = f"Erro ao clonar repositório: {clone_proc.stderr}"
                # Passo 6: Mensagem de erro mais clara se não houver token
                if 'not found' in clone_proc.stderr and not token:
                    error_msg += " Repositório não encontrado. Verifique se o repositório existe e se as credenciais (token) estão configuradas corretamente no Azure Key Vault."
                result["errors"].append(error_msg)
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
            parts = repo_name.split('/')
            if len(parts) != 3:
                raise ValueError(f"Nome do repositório Azure inválido. Formato esperado: 'organization/project/repository'. Recebido: '{repo_name}'")
            organization, project, repository = parts
            return f"https://dev.azure.com/{organization}/{project}/_git/{repository}"
        elif repository_type == "github":
            parts = repo_name.split('/')
            if len(parts) < 2:
                raise ValueError(f"Nome do repositório GitHub inválido. Formato esperado: 'organization/repository'. Recebido: '{repo_name}'")
            return f"https://github.com/{repo_name}.git"
        elif repository_type == "gitlab":
            return f"https://gitlab.com/{repo_name}.git"
        return repo_name

    def _inject_token_into_url(self, base_url: str, token: str, repository_type: str) -> str:
        if repository_type == "azure":
            if base_url.startswith("https://"):
                return base_url.replace("https://", f"https://{token}@", 1)
            else:
                return base_url
        elif repository_type == "github":
            if base_url.startswith("https://"):
                return base_url.replace("https://", f"https://{token}@", 1)
            else:
                return base_url
        elif repository_type == "gitlab":
            if base_url.startswith("https://"):
                return base_url.replace("https://", f"https://oauth2:{token}@", 1)
            else:
                return base_url
        return base_url

    def _mask_token_in_url(self, url: str) -> str:
        if '@' in url:
            prefix, rest = url.split('@', 1)
            if len(prefix) > 12:
                masked = prefix[:8] + '***' + prefix[-2:]
            else:
                masked = '***'
            return masked + '@' + rest
        return url

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
