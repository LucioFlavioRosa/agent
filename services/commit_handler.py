from typing import Dict, Any, Optional
from tools.conectores.conexao_geral import ConexaoGeral
from tools.repo_committers.orchestrator import processar_branch_por_provedor
from tools.repository_provider_factory import get_repository_provider_explicit
from tools.repo_committers.branch_name_sanitizer import BranchNameSanitizer
import json
from services.dotnet_build_service import DotNetBuildService
from tools.azure_secret_manager import AzureSecretManager
from models import JobFields

class CommitHandler:
    def __init__(self, repository_provider_factory=None, conexao_geral_factory=None, dotnet_build_service=None, secret_manager=None):
        self.repository_provider_factory = repository_provider_factory or get_repository_provider_explicit
        self.conexao_geral_factory = conexao_geral_factory or ConexaoGeral.create_with_defaults
        self.dotnet_build_service = dotnet_build_service or DotNetBuildService()
        self.secret_manager = secret_manager or AzureSecretManager()

    def execute_commits(self, job_id: str, job_info: Dict[str, Any], dados_finais_formatados: Dict[str, Any], 
                        repository_type: str, repo_name: str) -> None:
        print(f"[{job_id}] [DEBUG] INICIO execute_commits: executar_build_dotnet={job_info.get('data', {}).get('executar_build_dotnet')}")
        print(f"[{job_id}] BLINDAGEM: Iniciando execute_commits")
        try:
            branch_base_para_pr = job_info['data'].get('branch_name_modernizado')
            if not branch_base_para_pr:
                branch_base_para_pr = job_info['data'].get('branch_name', 'main')
            print(f"[{job_id}] Definida a branch de origem/alvo para o PR: '{branch_base_para_pr}'")
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
                    "arquivos_modificados": [],
                    "commit_url": None,
                    "build_result": None,
                    "build_errors": None
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
                    "arquivos_modificados": [],
                    "commit_url": None,
                    "build_result": None,
                    "build_errors": None
                }]
                print(f"[{job_id}] BLINDAGEM: commit_details definido com erro de formato")
                return
            executar_build_dotnet = job_info.get('data', {}).get('executar_build_dotnet', False)
            print(f"[{job_id}] [DEBUG] Loop de grupos: executar_build_dotnet extraído={executar_build_dotnet}")
            for i, grupo in enumerate(grupos):
                grupo_titulo = grupo.get('titulo_pr', f'Grupo {i+1}')
                print(f"[{job_id}] Processando grupo {i+1}/{len(grupos)}: {grupo_titulo}")
                conjunto_de_mudancas = grupo.get("conjunto_de_mudancas", [])
                if not isinstance(conjunto_de_mudancas, list):
                    print(f"[{job_id}] ERRO: conjunto_de_mudancas do grupo {i+1} não é uma lista. Valor: {conjunto_de_mudancas}")
                    conjunto_de_mudancas = []
                branch_sugerida = grupo.get("branch_sugerida", f"branch-grupo-{i+1}")
                branch_sugerida = BranchNameSanitizer.sanitize(branch_sugerida)
                build_result = None  
                build_errors = None 
                resultado_branch = None
                LIMITE_DESCRICAO_AZURE = 3900 
                descricao_completa = grupo.get("resumo_do_pr", f"Mudanças do grupo {i+1}")
                if len(descricao_completa) > LIMITE_DESCRICAO_AZURE:
                    descricao_pr = descricao_completa[:LIMITE_DESCRICAO_AZURE] + "\n\n...(descrição truncada para não exceder o limite da API)..."
                    print(f"[{job_id}] AVISO: A descrição do PR do grupo {i+1} foi truncada por ser muito longa.")
                else:
                    descricao_pr = descricao_completa
                try:
                    resultado_branch = processar_branch_por_provedor(
                        repo=repo,
                        nome_branch=branch_sugerida,
                        branch_de_origem=branch_base_para_pr,
                        branch_alvo_do_pr=branch_base_para_pr,
                        mensagem_pr=grupo.get("titulo_pr", f"PR Grupo {i+1}"),
                        descricao_pr=descricao_pr,
                        conjunto_de_mudancas=conjunto_de_mudancas,
                        repository_type=repository_type
                    )
                    print(f"[{job_id}] [DEBUG][CommitHandler] resultado_branch (após processar_branch_por_provedor): {json.dumps(resultado_branch, default=str)}")
                    resultado_branch = self._validate_and_fix_pr_url(job_id, resultado_branch, i+1)
                    if 'commit_url' not in resultado_branch:
                        resultado_branch['commit_url'] = None
                    if executar_build_dotnet:
                        branch_name = resultado_branch.get('branch_name')
                        repo_name_commit = job_info['data'].get('repo_name', repo_name)
                        token = None
                        try:
                            token = self._get_access_token(repository_type, repo_name_commit)
                        except Exception as e_token:
                            print(f"[{job_id}] [CommitHandler] Falha ao obter token: {e_token}")
                            build_errors = [f"Erro ao obter token: {str(e_token)}"]
                        print(f"[{job_id}] [CommitHandler][BUILD] Iniciando build. repository_type={repository_type}, repo_name={repo_name_commit}, branch_name={branch_name}, access_token presente: {bool(token)}")
                        try:
                            build_result = self.dotnet_build_service.build_project(
                                job_id=job_id,
                                repository_type=repository_type,
                                repo_name=repo_name_commit,
                                branch_name=branch_name,
                                access_token=token
                            )
                            print(f"[{job_id}] [CommitHandler][BUILD] Build finalizado. success={build_result.get('success')}, errors={len(build_result.get('errors', []))}, build_result={json.dumps(build_result, default=str)[:300]}")
                            if not build_result.get('success'):
                                if build_errors is None:
                                    build_errors = []
                                build_errors.extend(build_result.get('errors', []))
                        except Exception as e_build:
                            print(f"[{job_id}] [CommitHandler][BUILD] Exceção no build: {e_build}")
                            if build_errors is None:
                                build_errors = []
                            build_errors.append(str(e_build))
                            build_result = {"success": False, "errors": [str(e_build)]}
                        print(f"[{job_id}] [CommitHandler][BUILD] build_result será adicionado ao commit_info: {json.dumps(build_result, default=str)[:300]}")
                    commit_info = {
                        "branch_name": resultado_branch.get('branch_name'),
                        "success": resultado_branch.get('success'),
                        "pr_url": resultado_branch.get('pr_url'),
                        "message": resultado_branch.get('message'),
                        "arquivos_modificados": resultado_branch.get('arquivos_modificados', []),
                        "commit_url": resultado_branch.get('commit_url'),
                        "build_result": build_result,
                        "build_errors": build_errors
                    }
                    if resultado_branch.get('success') and (not commit_info.get('pr_url') or not isinstance(commit_info.get('pr_url'), str) or not commit_info.get('pr_url').strip()):
                        print(f"[{job_id}] [ERRO CRÍTICO] Resultado marcado como sucesso mas pr_url inválido: {json.dumps(resultado_branch, default=str)}")
                        raise Exception(f"[CommitHandler] Resultado marcado como sucesso mas pr_url inválido: {json.dumps(resultado_branch, default=str)}")
                except Exception as e:
                    print(f"[{job_id}] ERRO no processamento do grupo {i+1}: {str(e)}")
                    pr_url = None
                    commit_url = None
                    if resultado_branch and isinstance(resultado_branch, dict):
                        pr_url = resultado_branch.get('pr_url')
                        commit_url = resultado_branch.get('commit_url')
                    if pr_url and isinstance(pr_url, str) and pr_url.strip():
                        pr_url_final = pr_url
                    else:
                        pr_url_final = f"ERRO: Falha no processamento do grupo {i+1}. {str(e)}"
                    commit_info = {
                        "branch_name": branch_sugerida,
                        "success": False,
                        "pr_url": pr_url_final,
                        "message": f"Erro no grupo {i+1}: {str(e)}",
                        "arquivos_modificados": [arquivo.get('caminho_do_arquivo', '') for arquivo in conjunto_de_mudancas],
                        "commit_url": commit_url,
                        "build_result": build_result,
                        "build_errors": build_errors if build_errors else [str(e)]
                    }
                print(f"[{job_id}] DIAGNÓSTICO - Resultado do grupo {i+1}: success={commit_info.get('success')}, pr_url='{commit_info.get('pr_url')}', branch_name='{commit_info.get('branch_name')}', commit_url='{commit_info.get('commit_url')}', build_result={commit_info.get('build_result')}, build_errors={commit_info.get('build_errors')}")
                commit_results.append(commit_info)
            print(f"[{job_id}] [DEBUG] Pós-loop grupos: commit_results contém build_result/build_errors?")
            for idx, res in enumerate(commit_results):
                print(f"[{job_id}] [DEBUG] Grupo {idx+1}: build_result presente={ 'build_result' in res }, build_errors presente={ 'build_errors' in res }, build_result={res.get('build_result')}")
            print(f"[{job_id}] Commit concluído. Resultados: {len(commit_results)} branches processadas")
            print(f"[{job_id}] DIAGNÓSTICO FINAL - commit_results antes de salvar: {json.dumps(commit_results, default=str)}")
            for i, result in enumerate(commit_results):
                print(f"[{job_id}] DIAGNÓSTICO - PR {i+1}: pr_url='{result.get('pr_url')}', branch_name='{result.get('branch_name')}', success={result.get('success')}, arquivos_modificados={len(result.get('arquivos_modificados', []) )}, commit_url='{result.get('commit_url')}', build_result='{result.get('build_result')}', build_errors='{result.get('build_errors')}'")
            print(f"[{job_id}] BLINDAGEM: execute_commits concluído com sucesso")
            job_info['data']['commit_details'] = commit_results
        except Exception as e:
            print(f"[{job_id}] ERRO CRÍTICO em execute_commits: {str(e)}")
            if 'commit_details' not in job_info.get('data', {}):
                job_info['data']['commit_details'] = [{
                    "branch_name": "erro-geral",
                    "success": False,
                    "pr_url": f"ERRO: Falha geral no commit. {str(e)}",
                    "message": f"Erro geral: {str(e)}",
                    "arquivos_modificados": [],
                    "commit_url": None,
                    "build_result": None,
                    "build_errors": [str(e)]
                }]
            print(f"[{job_id}] BLINDAGEM: Erro geral tratado, commit_details garantido")
            raise e

    def _validate_and_fix_pr_url(self, job_id: str, resultado_branch: Dict[str, Any], grupo_num: int) -> Dict[str, Any]:
        print(f"[DEBUG][CommitHandler] _validate_and_fix_pr_url: job_id={job_id}, grupo_num={grupo_num}, pr_url={resultado_branch.get('pr_url')}, success={resultado_branch.get('success')}, branch_name={resultado_branch.get('branch_name')}")
        pr_url = resultado_branch.get('pr_url')
        success = resultado_branch.get('success', False)
        if success:
            if not pr_url or not isinstance(pr_url, str) or not pr_url.strip():
                raise Exception(f"[CommitHandler] Resultado marcado como sucesso mas pr_url inválido: {json.dumps(resultado_branch, default=str)}")
            if self._is_valid_url(pr_url):
                pass
            else:
                print(f"[{job_id}] AVISO: Grupo {grupo_num} tem pr_url que não é uma URL válida: '{pr_url}'")
                if "Branch processada" in str(pr_url) or "PR criado" in str(pr_url):
                    pass
                else:
                    resultado_branch['pr_url'] = f"AVISO: PR criado mas URL inválida retornada: {pr_url}"
        else:
            if not pr_url or not isinstance(pr_url, str) or not pr_url.strip():
                resultado_branch['pr_url'] = f"ERRO: Falha na criação do PR (Grupo {grupo_num}). Verifique logs."
        if resultado_branch.get('success') and (not resultado_branch.get('pr_url') or not isinstance(resultado_branch.get('pr_url'), str) or not resultado_branch.get('pr_url').strip()):
            raise Exception(f"[CommitHandler] Resultado marcado como sucesso mas pr_url inválido: {json.dumps(resultado_branch, default=str)}")
        print(f"[DEBUG][CommitHandler] _validate_and_fix_pr_url (final): pr_url={resultado_branch.get('pr_url')}")
        return resultado_branch

    def _is_valid_url(self, url: str) -> bool:
        if not url or not isinstance(url, str):
            return False
        return url.startswith('http://') or url.startswith('https://') or "Branch processada" in url or "PR criado" in url

    def _get_access_token(self, repository_type: str, repo_name: str) -> Optional[str]:
        if repository_type == 'azure':
            parts = repo_name.split('/')
            if len(parts) != 3:
                raise ValueError(f"Nome do repositório '{repo_name}' tem formato inválido para Azure.")
            org_name = parts[0]
            platform = 'Azure'
        elif repository_type == 'github':
            org_name = repo_name.strip().split('/')[0]
            platform = 'GitHub'
        elif repository_type == 'gitlab':
            org_name = repo_name.strip().split('/')[0]
            platform = 'GitLab'
        else:
            raise ValueError(f"Tipo de repositório '{repository_type}' não suportado para obtenção de token.")
        token_secret_name = f"{platform.lower()}-token-{org_name}"
        try:
            token = self.secret_manager.get_secret(token_secret_name)
            return token
        except Exception:
            try:
                token = self.secret_manager.get_secret(f"{platform.lower()}-token")
                return token
            except Exception:
                raise ValueError(f"Não foi possível obter token para {platform} ({org_name})")
