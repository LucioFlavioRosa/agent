from typing import Dict, Any
from tools.conectores.conexao_geral import ConexaoGeral
from tools.repo_committers.orchestrator import processar_branch_por_provedor
from tools.repository_provider_factory import get_repository_provider_explicit
from tools.repo_committers.branch_name_sanitizer import BranchNameSanitizer
from services.dotnet_build_service import DotNetBuildService
import tempfile
import shutil
import os
from models import JobFields

class CommitHandler:
    def __init__(self, repository_provider_factory=None, conexao_geral_factory=None):
        self.repository_provider_factory = repository_provider_factory or get_repository_provider_explicit
        self.conexao_geral_factory = conexao_geral_factory or ConexaoGeral.create_with_defaults
    
    def execute_commits(self, job_id: str, job_info: Dict[str, Any], dados_finais_formatados: Dict[str, Any], 
                      repository_type: str, repo_name: str, executar_build_dotnet: bool = False) -> None:
        print(f"[{job_id}] BLINDAGEM: Iniciando execute_commits")
        print(f"[{job_id}] DIAGNÓSTICO - Estrutura de dados_finais_formatados recebida: {dados_finais_formatados}")
        try:
            branch_base_para_pr = job_info['data'].get('branch_name', 'main')
            print(f"[{job_id}] Iniciando commit com repositório: '{repo_name}' (tipo: {repository_type})")
            try:
                repository_provider = self.repository_provider_factory(repository_type)
                conexao_geral = self.conexao_geral_factory()
                repo = conexao_geral.connection(
                    repositorio=repo_name,
                    repository_type=repository_type,
                    repository_provider=repository_provider
                )
            except Exception as e:
                print(f"[{job_id}] ERRO CRÍTICO: Falha ao conectar com repositório: {str(e)}")
                job_info['data']['commit_details'] = [{
                    "branch_name": "erro-conexao",
                    "success": False,
                    "pr_url": f"ERRO: Falha na conexão com repositório. {str(e)}",
                    "message": f"Erro de conexão: {str(e)}",
                    "arquivos_modificados": []
                }]
                print(f"[{job_id}] BLINDAGEM: Erro de conexão tratado, commit_details definido")
                return
            commit_results = []
            grupos = dados_finais_formatados.get("grupos", [])
            if not grupos or not isinstance(grupos, list):
                print(f"[{job_id}] ERRO: Formato de entrada de dados_finais_formatados['grupos'] está vazio ou malformado: {grupos}")
                job_info['data']['commit_details'] = [{
                    "branch_name": "erro-formato",
                    "success": False,
                    "pr_url": "ERRO: Formato de entrada de grupos está vazio ou malformado.",
                    "message": "Formato de entrada de grupos está vazio ou malformado.",
                    "arquivos_modificados": []
                }]
                print(f"[{job_id}] BLINDAGEM: commit_details definido com erro de formato")
                return
            modo_adicao_incremental = job_info.get('data', {}).get('modo_adicao_incremental', False)
            for i, grupo in enumerate(grupos):
                grupo_titulo = grupo.get('titulo_pr', f'Grupo {i+1}')
                print(f"[{job_id}] Processando grupo {i+1}/{len(grupos)}: {grupo_titulo}")
                try:
                    conjunto_de_mudancas = grupo.get("conjunto_de_mudancas", [])
                    if not isinstance(conjunto_de_mudancas, list):
                        print(f"[{job_id}] ERRO: conjunto_de_mudancas do grupo {i+1} não é uma lista. Valor: {conjunto_de_mudancas}")
                        conjunto_de_mudancas = []
                    branch_sugerida = grupo.get("branch_sugerida", f"branch-grupo-{i+1}")
                    branch_sugerida = BranchNameSanitizer.sanitize(branch_sugerida)
                    resultado_branch = processar_branch_por_provedor(
                        repo=repo,
                        nome_branch=branch_sugerida,
                        branch_de_origem=branch_base_para_pr,
                        branch_alvo_do_pr=branch_base_para_pr,
                        mensagem_pr=grupo.get("titulo_pr", f"PR Grupo {i+1}"),
                        descricao_pr=grupo.get("resumo_do_pr", f"Mudanças do grupo {i+1}"),
                        conjunto_de_mudancas=conjunto_de_mudancas,
                        repository_type=repository_type,
                        modo_adicao_incremental=modo_adicao_incremental
                    )
                    resultado_branch = self._validate_and_fix_pr_url(job_id, resultado_branch, i+1)
                except Exception as e:
                    print(f"[{job_id}] ERRO no processamento do grupo {i+1}: {str(e)}")
                    resultado_branch = {
                        "branch_name": branch_sugerida,
                        "success": False,
                        "pr_url": f"ERRO: Falha no processamento do grupo {i+1}. {str(e)}",
                        "message": f"Erro no grupo {i+1}: {str(e)}",
                        "arquivos_modificados": [arquivo.get('caminho_do_arquivo', '') for arquivo in conjunto_de_mudancas]
                    }
                print(f"[{job_id}] DIAGNÓSTICO - Resultado do grupo {i+1}: success={resultado_branch.get('success')}, pr_url='{resultado_branch.get('pr_url')}', branch_name='{resultado_branch.get('branch_name')}'")
                commit_results.append(resultado_branch)
            print(f"[{job_id}] Commit concluído. Resultados: {len(commit_results)} branches processadas")
            print(f"[{job_id}] DIAGNÓSTICO FINAL - commit_results antes de salvar: {commit_results}")
            job_info['data']['commit_details'] = commit_results
            print(f"[{job_id}] DIAGNÓSTICO - commit_details salvo no job_info: {job_info['data']['commit_details']}")
            for i, result in enumerate(commit_results):
                print(f"[{job_id}] DIAGNÓSTICO - PR {i+1}: pr_url='{result.get('pr_url')}', branch_name='{result.get('branch_name')}', success={result.get('success')}, arquivos_modificados={len(result.get('arquivos_modificados', []))}")
            if executar_build_dotnet:
                print(f"[{job_id}] [BUILD] Flag executar_build_dotnet=True. Iniciando validação de build .NET nas branches criadas.")
                build_errors_list = []
                for result in commit_results:
                    if result.get('success'):
                        branch_name = result.get('branch_name')
                        build_error = self._execute_dotnet_build_for_branch(job_id, repo_name, branch_name, repository_type)
                        if build_error:
                            if 'build_errors' not in result or not isinstance(result['build_errors'], list):
                                result['build_errors'] = []
                            result['build_errors'].append(build_error)
                            build_errors_list.append(build_error)
                job_info['data'][JobFields.BUILD_ERRORS] = build_errors_list if build_errors_list else None
            print(f"[{job_id}] BLINDAGEM: execute_commits concluído com sucesso")
        except Exception as e:
            print(f"[{job_id}] ERRO CRÍTICO em execute_commits: {str(e)}")
            if 'commit_details' not in job_info.get('data', {}):
                job_info['data']['commit_details'] = [{
                    "branch_name": "erro-geral",
                    "success": False,
                    "pr_url": f"ERRO: Falha geral no commit. {str(e)}",
                    "message": f"Erro geral: {str(e)}",
                    "arquivos_modificados": []
                }]
            print(f"[{job_id}] BLINDAGEM: Erro geral tratado, commit_details garantido")
            raise e
    
    def _validate_and_fix_pr_url(self, job_id: str, resultado_branch: Dict[str, Any], grupo_num: int) -> Dict[str, Any]:
        pr_url = resultado_branch.get('pr_url')
        success = resultado_branch.get('success', False)
        if success:
            if not pr_url or pr_url == "" or pr_url is None:
                print(f"[{job_id}] AVISO: Grupo {grupo_num} marcado como sucesso mas pr_url está vazio")
                resultado_branch['pr_url'] = f"AVISO: PR criado com sucesso mas URL não foi retornada pelo provedor (Grupo {grupo_num})"
            elif not self._is_valid_url(pr_url):
                print(f"[{job_id}] AVISO: Grupo {grupo_num} tem pr_url que não é uma URL válida: '{pr_url}'")
                if "Branch processada" in str(pr_url) or "PR criado" in str(pr_url):
                    pass
                else:
                    resultado_branch['pr_url'] = f"AVISO: PR criado mas URL inválida retornada: {pr_url}"
        else:
            if not pr_url or pr_url == "" or pr_url is None:
                resultado_branch['pr_url'] = f"ERRO: Falha na criação do PR (Grupo {grupo_num}). Verifique logs."
        return resultado_branch
    
    def _is_valid_url(self, url: str) -> bool:
        if not url or not isinstance(url, str):
            return False
        return url.startswith('http://') or url.startswith('https://') or "Branch processada" in url or "PR criado" in url

    def _execute_dotnet_build_for_branch(self, job_id: str, repo_name: str, branch_name: str, repository_type: str) -> str:
        print(f"[{job_id}] [BUILD] Iniciando build .NET para branch '{branch_name}' do repositório '{repo_name}' (tipo: {repository_type})")
        temp_dir = tempfile.mkdtemp(prefix=f"dotnet_build_{job_id}_")
        try:
            conexao_geral = self.conexao_geral_factory()
            repository_provider = self.repository_provider_factory(repository_type)
            print(f"[{job_id}] [BUILD] Clonando repositório para diretório temporário: {temp_dir}")
            repo_local = conexao_geral.clone_to_path(
                repositorio=repo_name,
                repository_type=repository_type,
                repository_provider=repository_provider,
                path=temp_dir
            )
            print(f"[{job_id}] [BUILD] Checkout da branch '{branch_name}'")
            if hasattr(repo_local, 'git'):
                repo_local.git.checkout(branch_name)
            elif hasattr(repo_local, 'checkout'):  # para outros providers
                repo_local.checkout(branch_name)
            else:
                print(f"[{job_id}] [BUILD] AVISO: Não foi possível fazer checkout da branch '{branch_name}' (provider desconhecido)")
            build_service = DotNetBuildService()
            sucesso, erro = build_service.execute_build(temp_dir)
            if sucesso:
                print(f"[{job_id}] [BUILD] Build .NET bem-sucedido para branch '{branch_name}'")
                return None
            else:
                print(f"[{job_id}] [BUILD] Build .NET FALHOU para branch '{branch_name}'. Erro: {erro}")
                return erro
        except Exception as e:
            print(f"[{job_id}] [BUILD] ERRO CRÍTICO ao executar build .NET para branch '{branch_name}': {e}")
            return f"Erro crítico ao executar build .NET: {str(e)}"
        finally:
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"[{job_id}] [BUILD] AVISO: Falha ao remover diretório temporário '{temp_dir}': {e}")
