from typing import Dict, Any
from tools.conectores.conexao_geral import ConexaoGeral
from tools.repo_committers.orchestrator import processar_branch_por_provedor
from tools.repository_provider_factory import get_repository_provider_explicit
from tools.repo_committers.branch_name_sanitizer import BranchNameSanitizer
from tools.repo_committers.path_validator import PathValidator
import json
from services.dotnet_build_service import DotNetBuildService

class CommitHandler:
    def __init__(self, repository_provider_factory=None, conexao_geral_factory=None, dotnet_build_service=None):
        self.repository_provider_factory = repository_provider_factory or get_repository_provider_explicit
        self.conexao_geral_factory = conexao_geral_factory or ConexaoGeral.create_with_defaults
        self.dotnet_build_service = dotnet_build_service or DotNetBuildService()
    
    def execute_commits(self, job_id: str, job_info: Dict[str, Any], dados_finais_formatados: Dict[str, Any], 
                      repository_type: str, repo_name: str, usuario_executor=None) -> None:
        print(f"[{job_id}] [DEBUG] INICIO execute_commits: executar_build_dotnet={job_info.get('data', {}).get('executar_build_dotnet')}")
        print(f"[{job_id}] BLINDAGEM: Iniciando execute_commits")
        print(f"[{job_id}] DIAGNÓSTICO - Estrutura de dados_finais_formatados recebida: {dados_finais_formatados}")
        print(f"[{job_id}] [LOG] Parâmetros de conexão: repository_type={repository_type}, repo_name={repo_name}")
        # Validação explícita dos dados antes de prosseguir
        if not dados_finais_formatados or 'grupos' not in dados_finais_formatados or not isinstance(dados_finais_formatados['grupos'], list) or len(dados_finais_formatados['grupos']) == 0:
            print(f"[{job_id}] [ERRO] Estrutura de dados_finais_formatados inválida ou grupos vazio/malformado: {dados_finais_formatados}")
            if 'data' in job_info:
                job_info['data']['commit_details'] = [{
                    "branch_name": "erro-formato",
                    "success": False,
                    "pr_url": "ERRO: Estrutura de entrada de dados_finais_formatados['grupos'] está vazia, ausente ou malformada.",
                    "message": "Estrutura de entrada de grupos está vazia, ausente ou malformada.",
                    "arquivos_modificados": [],
                    "commit_url": None
                }]
            else:
                job_info['commit_details'] = [{
                    "branch_name": "erro-formato",
                    "success": False,
                    "pr_url": "ERRO: Estrutura de entrada de dados_finais_formatados['grupos'] está vazia, ausente ou malformada.",
                    "message": "Estrutura de entrada de grupos está vazia ou malformada.",
                    "arquivos_modificados": [],
                    "commit_url": None
                }]
            return
        try:
            branch_base_para_pr = job_info['data'].get('branch_name', 'main')
            print(f"[{job_id}] Iniciando commit com repositório: '{repo_name}' (tipo: {repository_type})")
            # Validação robusta da conexão do repositório
            try:
                repository_provider = self.repository_provider_factory(repository_type)
                conexao_geral = self.conexao_geral_factory()
                repo = conexao_geral.connection(
                    repositorio=repo_name,
                    repository_type=repository_type,
                    repository_provider=repository_provider
                )
                if repo is None:
                    raise Exception(f"Falha ao conectar ao repositório: repo=None")
                # Validação de métodos esperados (GitHub: get_branch, get_contents, etc)
                if repository_type == 'github' and not (hasattr(repo, 'get_branch') and hasattr(repo, 'get_contents')):
                    raise Exception(f"Objeto repo não possui métodos esperados do GitHub")
                if repository_type == 'gitlab' and not hasattr(repo, 'branches'):
                    raise Exception(f"Objeto repo não possui atributo 'branches' do GitLab")
                if repository_type == 'azure' and not (hasattr(repo, 'id') or hasattr(repo, '_organization')):
                    raise Exception(f"Objeto repo não possui atributos esperados do Azure")
                print(f"[{job_id}] [LOG] Conexão com repositório estabelecida com sucesso.")
            except Exception as e:
                print(f"[{job_id}] ERRO CRÍTICO: Falha ao conectar com repositório: {str(e)}")
                job_info['data']['commit_details'] = [{
                    "branch_name": "erro-conexao",
                    "success": False,
                    "pr_url": f"ERRO: Falha na conexão com repositório. {str(e)}",
                    "message": f"Erro de conexão: {str(e)}",
                    "arquivos_modificados": [],
                    "commit_url": None
                }]
                print(f"[{job_id}] BLINDAGEM: Erro de conexão tratado, commit_details definido")
                return
            # Validação da existência da branch de origem
            try:
                branch_origem_existe = False
                if repository_type == 'github':
                    try:
                        repo.get_branch(branch_base_para_pr)
                        branch_origem_existe = True
                    except Exception as e:
                        print(f"[{job_id}] [ERRO] Branch de origem '{branch_base_para_pr}' não encontrada no GitHub: {e}")
                elif repository_type == 'gitlab':
                    try:
                        repo.branches.get(branch_base_para_pr)
                        branch_origem_existe = True
                    except Exception as e:
                        print(f"[{job_id}] [ERRO] Branch de origem '{branch_base_para_pr}' não encontrada no GitLab: {e}")
                elif repository_type == 'azure':
                    try:
                        # Azure: checa via API se branch existe
                        if hasattr(repo, '_organization') and hasattr(repo, '_project') and hasattr(repo, 'id'):
                            from tools.conectores.azure_conector import AzureConector
                            connector = AzureConector.create_with_defaults()
                            token = connector._get_token_for_org(repo._organization, platform='azure')
                            import requests
                            base_url = f"https://dev.azure.com/{repo._organization}/{repo._project}/_apis"
                            refs_url = f"{base_url}/git/repositories/{repo.id}/refs?filter=heads/{branch_base_para_pr}&api-version=7.0"
                            headers = {
                                "Content-Type": "application/json",
                                "Authorization": f"Basic {token}"
                            }
                            refs_response = requests.get(refs_url, headers=headers, timeout=30)
                            refs_response.raise_for_status()
                            refs_data = refs_response.json()
                            if refs_data.get('value'):
                                branch_origem_existe = True
                    except Exception as e:
                        print(f"[{job_id}] [ERRO] Branch de origem '{branch_base_para_pr}' não encontrada no Azure: {e}")
                if not branch_origem_existe:
                    print(f"[{job_id}] [ERRO] Branch de origem '{branch_base_para_pr}' não existe no repositório remoto. Commit abortado.")
                    job_info['data']['commit_details'] = [{
                        "branch_name": "erro-branch-origem",
                        "success": False,
                        "pr_url": f"ERRO: Branch de origem '{branch_base_para_pr}' não existe no repositório remoto.",
                        "message": f"Branch de origem '{branch_base_para_pr}' não existe no repositório remoto.",
                        "arquivos_modificados": [],
                        "commit_url": None
                    }]
                    return
            except Exception as e:
                print(f"[{job_id}] [ERRO] Falha ao validar existência da branch de origem: {e}")
                job_info['data']['commit_details'] = [{
                    "branch_name": "erro-validacao-branch-origem",
                    "success": False,
                    "pr_url": f"ERRO: Falha ao validar existência da branch de origem: {e}",
                    "message": f"Falha ao validar existência da branch de origem: {e}",
                    "arquivos_modificados": [],
                    "commit_url": None
                }]
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
                    "commit_url": None
                }]
                print(f"[{job_id}] BLINDAGEM: commit_details definido com erro de formato")
                return
            modo_adicao_incremental = job_info.get('data', {}).get('modo_adicao_incremental', False)
            executar_build_dotnet = job_info.get('data', {}).get('executar_build_dotnet', False)
            if usuario_executor is None:
                usuario_executor = job_info.get('data', {}).get('usuario_executor')
            print(f"[{job_id}] [DEBUG] Loop de grupos: executar_build_dotnet extraído={executar_build_dotnet}")
            for i, grupo in enumerate(grupos):
                grupo_titulo = grupo.get('titulo_pr', f'Grupo {i+1}')
                branch_sugerida = grupo.get("branch_sugerida", f"branch-grupo-{i+1}")
                print(f"[{job_id}] [LOG] Processando grupo {i+1}/{len(grupos)}: titulo='{grupo_titulo}', branch_sugerida='{branch_sugerida}', num_mudancas={len(grupo.get('conjunto_de_mudancas', []))}")
                try:
                    conjunto_de_mudancas = grupo.get("conjunto_de_mudancas", [])
                    if not isinstance(conjunto_de_mudancas, list):
                        print(f"[{job_id}] ERRO: conjunto_de_mudancas do grupo {i+1} não é uma lista. Valor: {conjunto_de_mudancas}")
                        conjunto_de_mudancas = []
                    branch_sugerida = BranchNameSanitizer.sanitize(branch_sugerida)
                    print(f"[{job_id}] [DEBUG][NORMALIZACAO] Antes da normalização das chaves do conjunto_de_mudancas do grupo {i+1}: {json.dumps(conjunto_de_mudancas, default=str)}")
                    conjunto_de_mudancas_normalizado = []
                    for mudanca in conjunto_de_mudancas:
                        mudanca_normalizada = PathValidator.normalize_change_keys(mudanca)
                        conjunto_de_mudancas_normalizado.append(mudanca_normalizada)
                    print(f"[{job_id}] [DEBUG][NORMALIZACAO] Depois da normalização das chaves do conjunto_de_mudancas do grupo {i+1}: {json.dumps(conjunto_de_mudancas_normalizado, default=str)}")
                    print(f"[{job_id}] [VALIDACAO] Validando caminhos do conjunto_de_mudancas do grupo {i+1} (total: {len(conjunto_de_mudancas_normalizado)})")
                    mudancas_validas = []
                    mudancas_invalidas = []
                    for idx_m, mudanca in enumerate(conjunto_de_mudancas_normalizado):
                        caminho = mudanca.get("caminho")
                        try:
                            caminho_validado = PathValidator.validate_path(mudanca)
                            mudanca["caminho"] = caminho_validado
                            mudancas_validas.append(mudanca)
                        except Exception as e:
                            print(f"[{job_id}] [ERRO][commit_handler] Grupo {i+1}, Mudança {idx_m}: caminho inválido: '{caminho}'. Erro: {e}")
                            mudancas_invalidas.append({"indice": idx_m, "caminho": caminho, "erro": str(e)})
                    print(f"[{job_id}] [VALIDACAO] Grupo {i+1}: {len(mudancas_validas)} mudanças validadas, {len(mudancas_invalidas)} rejeitadas.")
                    if len(mudancas_validas) == 0:
                        job_info['data']['commit_details'] = [{
                            "branch_name": branch_sugerida,
                            "success": False,
                            "pr_url": f"ERRO: Nenhuma mudança válida para commitar no grupo {i+1}. Mudanças inválidas: {mudancas_invalidas}",
                            "message": f"Nenhuma mudança válida para commitar no grupo {i+1}.",
                            "arquivos_modificados": [],
                            "commit_url": None
                        }]
                        print(f"[{job_id}] [ERRO] Todas as mudanças do grupo {i+1} foram rejeitadas por caminho inválido. Pulando grupo.")
                        continue
                    resultado_branch = processar_branch_por_provedor(
                        repo=repo,
                        nome_branch=branch_sugerida,
                        branch_de_origem=branch_base_para_pr,
                        branch_alvo_do_pr=branch_base_para_pr,
                        mensagem_pr=grupo.get("titulo_pr", f"PR Grupo {i+1}"),
                        descricao_pr=grupo.get("resumo_do_pr", f"Mudanças do grupo {i+1}"),
                        conjunto_de_mudancas=mudancas_validas,
                        repository_type=repository_type,
                        modo_adicao_incremental=modo_adicao_incremental
                    )
                    resultado_branch = self._validate_and_fix_pr_url(job_id, resultado_branch, i+1)
                    if 'commit_url' not in resultado_branch:
                        resultado_branch['commit_url'] = None
                    if executar_build_dotnet:
                        print(f"[{job_id}] [DEBUG] Antes do build: executar_build_dotnet={executar_build_dotnet}, branch={branch_sugerida}, commit_details presente: {job_info.get('data', {}).get('commit_details') is not None}")
                        build_result = self.dotnet_build_service.build_project(
                            job_id=job_id,
                            repository_type=repository_type,
                            repo_name=repo_name,
                            branch_name=branch_sugerida,
                            usuario_executor=usuario_executor
                        )
                        print(f"[{job_id}] [DEBUG] Resultado do build: success={build_result.get('success')}, errors={len(build_result.get('errors', []) )}")
                        resultado_branch["build_result"] = build_result
                        if not build_result.get("success", False):
                            resultado_branch["build_errors"] = build_result.get("errors", [])
                except Exception as e:
                    print(f"[{job_id}] ERRO no processamento do grupo {i+1}: {str(e)}")
                    resultado_branch = {
                        "branch_name": branch_sugerida,
                        "success": False,
                        "pr_url": f"ERRO: Falha no processamento do grupo {i+1}. {str(e)}",
                        "message": f"Erro no grupo {i+1}: {str(e)}",
                        "arquivos_modificados": [arquivo.get('caminho', '') for arquivo in conjunto_de_mudancas],
                        "commit_url": None
                    }
                print(f"[{job_id}] [LOG] Resultado do grupo {i+1}: success={resultado_branch.get('success')}, pr_url='{resultado_branch.get('pr_url')}', branch_name='{resultado_branch.get('branch_name')}', commit_url='{resultado_branch.get('commit_url')}', arquivos_modificados={len(resultado_branch.get('arquivos_modificados', []))}")
                commit_results.append(resultado_branch)
            print(f"[{job_id}] [LOG] Pós-loop grupos: commit_results contém build_result/build_errors?")
            for idx, res in enumerate(commit_results):
                print(f"[{job_id}] [LOG] Grupo {idx+1}: build_result presente={ 'build_result' in res }, build_errors presente={ 'build_errors' in res }, build_result={res.get('build_result')}")
            print(f"[{job_id}] Commit concluído. Resultados: {len(commit_results)} branches processadas")
            print(f"[{job_id}] [LOG] DIAGNÓSTICO FINAL - commit_results antes de salvar: {json.dumps(commit_results, default=str)}")
            for i, result in enumerate(commit_results):
                print(f"[{job_id}] [LOG] PR {i+1}: pr_url='{result.get('pr_url')}', branch_name='{result.get('branch_name')}', success={result.get('success')}, arquivos_modificados={len(result.get('arquivos_modificados', []) )}, commit_url='{result.get('commit_url')}'")
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
                    "commit_url": None
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
            if not self._is_valid_url(pr_url):
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
