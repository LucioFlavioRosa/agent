import subprocess
import os
from typing import Tuple, Optional

class DotNetBuildService:
    def execute_build(self, repo_path: str) -> Tuple[bool, Optional[str]]:
        if not os.path.isdir(repo_path):
            return False, f"Erro: O diretório '{repo_path}' não foi encontrado."
        command = ["dotnet", "build"]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                cwd=repo_path
            )
            return True, result.stdout
        except FileNotFoundError:
            return False, "Erro: O comando 'dotnet' não foi encontrado. Verifique se o .NET SDK está instalado e no PATH do sistema."
        except subprocess.CalledProcessError as e:
            return False, e.stderr
