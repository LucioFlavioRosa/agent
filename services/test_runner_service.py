import os
import subprocess
import time
import sys
from typing import List, Dict, Any
import glob
import re

class TestRunnerService:
    def __init__(self):
        pass

    def run_tests_for_files(self, file_paths: List[str], repository_path: str, layer: str = None, execute_integration_tests: bool = False, job_id: str = None) -> Dict[str, Any]:
        start_time = time.time()
        test_files = self._find_related_test_files(file_paths, repository_path)
        results = []
        integration_results = []
        output = ''
        success = True
        execution_time = 0.0
        if not test_files:
            output = 'Nenhum teste relacionado encontrado para os arquivos modificados.'
        else:
            for test_file in test_files:
                result = self._run_pytest_on_file(test_file, repository_path)
                results.append(result)
            success = all(r['success'] for r in results)
            output = '\n\n'.join(r['output'] for r in results)
        execution_time = time.time() - start_time
        integration_test_files = []
        integration_success = True
        integration_output = ''
        integration_execution_time = 0.0
        if execute_integration_tests:
            integration_test_files = self._find_integration_test_files(repository_path)
            if job_id is not None and layer is not None:
                print(f"[{job_id}] Executando {len(integration_test_files)} testes de integração para camada {layer}")
            integration_start_time = time.time()
            for integration_test_file in integration_test_files:
                result = self._run_pytest_on_file(integration_test_file, repository_path, timeout=300)
                integration_results.append(result)
            integration_success = all(r['success'] for r in integration_results)
            integration_output = '\n\n'.join(r['output'] for r in integration_results)
            integration_execution_time = time.time() - integration_start_time
        return {
            'success': success and integration_success,
            'output': output,
            'test_files': test_files,
            'execution_time': execution_time,
            'integration_tests_executed': execute_integration_tests,
            'integration_test_files': integration_test_files,
            'integration_success': integration_success,
            'integration_output': integration_output,
            'integration_execution_time': integration_execution_time
        }

    def run_all_tests(self, repository_path: str) -> Dict[str, Any]:
        start_time = time.time()
        try:
            completed = subprocess.run(
                [sys.executable, '-m', 'pytest', repository_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=300
            )
            output = completed.stdout.decode('utf-8')
            success = completed.returncode == 0
        except subprocess.TimeoutExpired as e:
            output = f'Timeout ao executar toda a suite de testes: {str(e)}'
            success = False
        except Exception as e:
            output = f'Erro ao executar toda a suite de testes: {str(e)}'
            success = False
        execution_time = time.time() - start_time
        return {
            'success': success,
            'output': output,
            'execution_time': execution_time
        }

    def _find_related_test_files(self, file_paths: List[str], repository_path: str) -> List[str]:
        test_files = glob.glob(os.path.join(repository_path, 'tests', 'test_*.py'))
        related_tests = set()
        for test_file in test_files:
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                for file_path in file_paths:
                    module_name = self._extract_module_name(file_path)
                    if module_name and re.search(rf'import\s+{re.escape(module_name)}|from\s+{re.escape(module_name)}', content):
                        related_tests.add(test_file)
            except Exception:
                continue
        return list(related_tests)

    def _find_integration_test_files(self, repository_path: str) -> List[str]:
        integration_test_files = glob.glob(os.path.join(repository_path, 'tests', 'test_integration_*.py'))
        return integration_test_files

    def _extract_module_name(self, file_path: str) -> str:
        base = os.path.basename(file_path)
        if base.endswith('.py'):
            return base[:-3]
        return base

    def _run_pytest_on_file(self, test_file: str, repository_path: str, timeout: int = 120) -> Dict[str, Any]:
        try:
            completed = subprocess.run(
                [sys.executable, '-m', 'pytest', test_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=repository_path,
                timeout=timeout
            )
            output = completed.stdout.decode('utf-8')
            success = completed.returncode == 0
        except subprocess.TimeoutExpired as e:
            output = f'Timeout ao executar teste {test_file}: {str(e)}'
            success = False
        except Exception as e:
            output = f'Erro ao executar teste {test_file}: {str(e)}'
            success = False
        return {
            'success': success,
            'output': output,
            'test_file': test_file
        }
