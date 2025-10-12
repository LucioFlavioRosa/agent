import subprocess
import os
import shutil
from typing import Dict, Any, Optional, List

class DotNetBuildService:
    def __init__(self):
        pass

    def build_project(self, job_id: str, repository_type: str, repo_name: str, branch_name: str) -> Dict[str, Any]:
        result = {
            "success": False,
            "errors": [],
            "stdout": "",
            "stderr": ""
        }
        local_dir = f"/tmp/{job_id}_{branch_name}"
        try:
            clone_url = self._get_clone_url(repository_type, repo_name)
            if os.path.exists(local_dir):
                shutil.rmtree(local_dir)
            clone_cmd = ["git", "clone", "--branch", branch_name, clone_url, local_dir]
            clone_proc = subprocess.run(clone_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if clone_proc.returncode != 0:
                result["errors"].append(f"Erro ao clonar repositório: {clone_proc.stderr}")
                result["stderr"] = clone_proc.stderr
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
