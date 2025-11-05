from github import GithubException, UnknownObjectException
from typing import Dict, Any, List
from tools.repo_committers.base_committer import BaseCommitter
from tools.repo_committers.branch_name_sanitizer import BranchNameSanitizer
import json
import random
import string

def _gerar_sufixo_aleatorio(tamanho=6):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=tamanho))

def processar_branch_github(
    repo,
    nome_branch: str,
    branch_de_origem: str,
    branch_alvo_do_pr: str,
    mensagem_pr: str,
    descricao_pr: str,
    conjunto_de_mudancas: list
) -> Dict[str, Any]:
    resultado_branch = BaseCommitter._inicializar_resultado_branch(nome_branch)
    resultado_branch['commit_url'] = None
    sanitized = BranchNameSanitizer.sanitize(nome_branch)

    if sanitized != nome_branch or sanitized == "invalid-branch":
        msg = f"Nome da branch inválido para GitHub: '{nome_branch}' (sanitizado: '{sanitized}')"
        BaseCommitter._finalizar_resultado_erro(resultado_branch, msg)
        return resultado_branch

    valid, error_msg = BaseCommitter._validate_files_exist_in_source(conjunto_de_mudancas, repo, branch_de_origem, 'github')
    if not valid:
        BaseCommitter._finalizar_resultado_erro(resultado_branch, error_msg)
        return resultado_branch

    try:
        BaseCommitter._validate_no_duplicate_paths(conjunto_de_mudancas)
    except ValueError as ve:
        BaseCommitter._finalizar_resultado_erro(resultado_branch, str(ve))
        return resultado_branch

    commits_realizados = 0
    commit_url = None

    try:
        ref_base = repo.get_git_ref(f"heads/{branch_de_origem}")
        repo.create_git_ref(ref=f"refs/heads/{nome_branch}", sha=ref_base.object.sha)
    except GithubException as e:
        if e.status == 422 and "Reference already exists" in str(e.data):
            print(f"Branch '{nome_branch}' já existe. Continuando...")
            pass
        else:
            print(f"Erro ao criar branch '{nome_branch}': {e}")
            raise

    mudancas_validas = BaseCommitter._processar_mudancas_comuns(conjunto_de_mudancas, resultado_branch)

    for mudanca in mudancas_validas:
        caminho = mudanca["caminho"]
        status = mudanca["status"]
        conteudo = mudanca["conteudo"]
        sha_arquivo_existente = None
        arquivo_existente = None

        # --- CORREÇÃO 1: Buscar SHA para MODIFICADO e REMOVIDO ---
        if status in ("MODIFICADO", "REMOVIDO"):
            try:
                arquivo_existente = repo.get_contents(caminho, ref=nome_branch)
                sha_arquivo_existente = arquivo_existente.sha
            except UnknownObjectException:
                print(f"[AVISO] Arquivo '{caminho}' não encontrado na branch '{nome_branch}' para {status}. Pulando...")
                continue
            except Exception as e_sha:
                print(f"[ERRO] Falha ao obter SHA do arquivo '{caminho}': {e_sha}. Pulando...")
                continue
        
        # --- CORREÇÃO 2: Remover o try...except...pass silencioso ---
        try:
            if status in ("ADICIONADO", "CRIADO"):
                # Opcional: verificar se o arquivo já existe para evitar erro
                try:
                    repo.get_contents(caminho, ref=nome_branch)
                    print(f"[AVISO] Status é 'CRIADO' mas arquivo '{caminho}' já existe. Tentando atualizar (update)...")
                    # Se já existe, tratamos como update. Precisamos do SHA.
                    if not sha_arquivo_existente:
                         arquivo_existente = repo.get_contents(caminho, ref=nome_branch)
                         sha_arquivo_existente = arquivo_existente.sha
                    
                    commit_response = repo.update_file(path=caminho, message=f"refactor: {caminho}", content=conteudo or "", sha=sha_arquivo_existente, branch=nome_branch)

                except UnknownObjectException:
                    # Arquivo não existe, o que é o esperado. Criamos.
                    commit_response = repo.create_file(path=caminho, message=f"feat: {caminho}", content=conteudo or "", branch=nome_branch)
            
            elif status == "MODIFICADO":
                if not sha_arquivo_existente or not arquivo_existente:
                    print(f"[ERRO] Status 'MODIFICADO' para '{caminho}' mas SHA não foi encontrado. Pulando...")
                    continue
                commit_response = repo.update_file(path=caminho, message=f"refactor: {caminho}", content=conteudo or "", sha=sha_arquivo_existente, branch=nome_branch)

            elif status == "REMOVIDO":
                if not sha_arquivo_existente:
                    print(f"[ERRO] Status 'REMOVIDO' para '{caminho}' mas SHA não foi encontrado. Pulando...")
                    continue
                commit_response = repo.delete_file(path=caminho, message=f"refactor: remove {caminho}", sha=sha_arquivo_existente, branch=nome_branch)
            
            # Se chegou aqui, o commit (create/update/delete) foi tentado
            commits_realizados += 1
            print(f"[INFO] Commit realizado para '{caminho}' (Status: {status})")

            # Lógica para pegar a URL do commit (mantida)
            if commit_response and 'commit' in commit_response and hasattr(commit_response['commit'], 'html_url'):
                commit_url_candidate = getattr(commit_response['commit'], 'html_url', None)
                if commit_url_candidate and BaseCommitter._validate_commit_url(commit_url_candidate):
                    commit_url = commit_url_candidate
            elif commit_response and 'commit' in commit_response and 'url' in commit_response['commit']:
                commit_url_candidate = commit_response['commit']['url']
                if commit_url_candidate and BaseCommitter._validate_commit_url(commit_url_candidate):
                    commit_url = commit_url_candidate

        except GithubException as e_commit:
            # ERRO FATAL: O commit falhou. Agora nós logamos o porquê.
            print(f"[ERRO FATAL] Falha ao commitar arquivo '{caminho}' (Status: {status}).")
            print(f"[ERRO FATAL] Mensagem: {e_commit.data.get('message', str(e_commit))}")
            # Você pode decidir se quer parar o loop ou só pular este arquivo
            # raise e_commit # Descomente para parar todo o processo
            continue # Mantém o comportamento de pular o arquivo, mas agora com log

        except Exception as e_general:
            # Outro erro inesperado
            print(f"[ERRO FATAL] Erro inesperado ao processar '{caminho}': {e_general}")
            # raise e_general # Descomente para parar todo o processo
            continue # Mantém o comportamento de pular o arquivo, mas agora com log

    if commit_url and BaseCommitter._validate_commit_url(commit_url):
        resultado_branch['commit_url'] = commit_url
    else:
        resultado_branch['commit_url'] = None
    
    # --- O restante do seu código (criação do PR) continua aqui ---
    if commits_realizados > 0:
        # ... (lógica do PR) ...
        tentativas = 0
        while tentativas < 2:
            try:
                pr = repo.create_pull(title=mensagem_pr, body=descricao_pr or "Refatoração automática gerada pela plataforma de agentes de IA.", head=nome_branch, base=branch_alvo_do_pr)
                if not hasattr(pr, 'html_url') or pr.html_url is None or not isinstance(pr.html_url, str) or not pr.html_url.strip():
                    BaseCommitter._finalizar_resultado_erro(resultado_branch, f"PR criado mas html_url inválido: {json.dumps(pr.__dict__, default=str)}")
                    break
                BaseCommitter._finalizar_resultado_sucesso(resultado_branch, pr.html_url.strip())
                break
            except ValueError as ve:
                if tentativas == 0:
                    sufixo = _gerar_sufixo_aleatorio()
                    novo_titulo = f"{mensagem_pr}-retry-{sufixo}"
                    mensagem_pr = novo_titulo
                    tentativas += 1
                    continue
                else:
                    raise
            except GithubException as e:
                if e.status == 422 and "A pull request for these commits already exists" in str(e.data):
                    try:
                        # Tenta encontrar o PR existente
                        pulls = repo.get_pulls(state='open', head=f"{repo.owner.login}:{nome_branch}", base=branch_alvo_do_pr)
                        if pulls.totalCount > 0:
                            pr_url_existente = pulls[0].html_url
                            BaseCommitter._finalizar_resultado_sucesso(resultado_branch, pr_url=pr_url_existente, message="PR já existente.")
                        else:
                             BaseCommitter._finalizar_resultado_sucesso(resultado_branch, pr_url=f"PR criado para branch: {nome_branch}", message="PR já existente.")
                    except Exception as e_find_pr:
                         BaseCommitter._finalizar_resultado_sucesso(resultado_branch, pr_url=f"PR criado para branch: {nome_branch}", message="PR já existente (falha ao buscar URL).")
                    break
                else:
                    BaseCommitter._finalizar_resultado_erro(resultado_branch, f"Erro ao criar PR: {e.data.get('message', str(e))}")
                    break
            except Exception as e:
                BaseCommitter._finalizar_resultado_erro(resultado_branch, f"Erro crítico ao validar PR: {e}")
                break
    else:
        print(f"[AVISO] Nenhum commit foi realizado para a branch '{nome_branch}'. Não foi possível criar PR.")
        BaseCommitter._finalizar_resultado_erro(resultado_branch, "Nenhuma mudança válida para commitar.")
    
    return resultado_branch
