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
    conjunto_de_mudancas: list,
    modo_adicao_incremental: bool = False
) -> Dict[str, Any]:
    print(f"\n--- Processando Lote GitHub para a Branch: '{nome_branch}' ---")
    resultado_branch = BaseCommitter._inicializar_resultado_branch(nome_branch)
    resultado_branch['commit_url'] = None
    sanitized = BranchNameSanitizer.sanitize(nome_branch)
    if sanitized != nome_branch or sanitized == "invalid-branch":
        msg = f"Nome da branch inválido para GitHub: '{nome_branch}' (sanitizado: '{sanitized}')"
        print(f"[ERRO][GITHUB] {msg}")
        BaseCommitter._finalizar_resultado_erro(resultado_branch, msg)
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
        print(f"Branch '{nome_branch}' criada a partir de '{branch_de_origem}'.")
    except GithubException as e:
        if e.status == 422 and "Reference already exists" in str(e.data):
            print(f"AVISO: A branch '{nome_branch}' já existe. Commits serão adicionados a ela.")
        else:
            raise
    print(f"Iniciando aplicação de {len(conjunto_de_mudancas)} mudanças...")
    mudancas_validas = BaseCommitter._processar_mudancas_comuns(conjunto_de_mudancas, resultado_branch)
    for mudanca in mudancas_validas:
        caminho = mudanca["caminho"]
        status = mudanca["status"]
        conteudo = mudanca["conteudo"]
        try:
            sha_arquivo_existente = None
            arquivo_existente = None
            try:
                arquivo_existente = repo.get_contents(caminho, ref=nome_branch)
                sha_arquivo_existente = arquivo_existente.sha
            except UnknownObjectException:
                pass
            if status in ("ADICIONADO", "CRIADO"):
                if sha_arquivo_existente:
                    print(f"  [AVISO] Arquivo '{caminho}' marcado como ADICIONADO já existe. Será tratado como MODIFICADO.")
                    commit_response = repo.update_file(path=caminho, message=f"refactor: {caminho}", content=conteudo or "", sha=sha_arquivo_existente, branch=nome_branch)
                else:
                    commit_response = repo.create_file(path=caminho, message=f"feat: {caminho}", content=conteudo or "", branch=nome_branch)
                print(f"  [CRIADO/MODIFICADO] {caminho}")
                commits_realizados += 1
                if commit_response and 'commit' in commit_response and hasattr(commit_response['commit'], 'html_url'):
                    commit_url_candidate = getattr(commit_response['commit'], 'html_url', None)
                    if commit_url_candidate and BaseCommitter._validate_commit_url(commit_url_candidate):
                        commit_url = commit_url_candidate
                elif commit_response and 'commit' in commit_response and 'url' in commit_response['commit']:
                    commit_url_candidate = commit_response['commit']['url']
                    if commit_url_candidate and BaseCommitter._validate_commit_url(commit_url_candidate):
                        commit_url = commit_url_candidate
            elif status == "MODIFICADO":
                if not sha_arquivo_existente or not arquivo_existente:
                    print(f"  [ERRO] Arquivo '{caminho}' marcado como MODIFICADO não foi encontrado na branch. Ignorando.")
                    continue
                if modo_adicao_incremental:
                    conteudo_existente = arquivo_existente.decoded_content.decode('utf-8')
                    conteudo = BaseCommitter._mesclar_conteudo(conteudo_existente, conteudo)
                commit_response = repo.update_file(path=caminho, message=f"refactor: {caminho}", content=conteudo or "", sha=sha_arquivo_existente, branch=nome_branch)
                print(f"  [MODIFICADO] {caminho}")
                commits_realizados += 1
                if commit_response and 'commit' in commit_response and hasattr(commit_response['commit'], 'html_url'):
                    commit_url_candidate = getattr(commit_response['commit'], 'html_url', None)
                    if commit_url_candidate and BaseCommitter._validate_commit_url(commit_url_candidate):
                        commit_url = commit_url_candidate
                elif commit_response and 'commit' in commit_response and 'url' in commit_response['commit']:
                    commit_url_candidate = commit_response['commit']['url']
                    if commit_url_candidate and BaseCommitter._validate_commit_url(commit_url_candidate):
                        commit_url = commit_url_candidate
            elif status == "REMOVIDO":
                if not sha_arquivo_existente:
                    print(f"  [AVISO] Arquivo '{caminho}' marcado como REMOVIDO já não existe. Ignorando.")
                    continue
                commit_response = repo.delete_file(path=caminho, message=f"refactor: remove {caminho}", sha=sha_arquivo_existente, branch=nome_branch)
                print(f"  [REMOVIDO] {caminho}")
                commits_realizados += 1
                if commit_response and 'commit' in commit_response and hasattr(commit_response['commit'], 'html_url'):
                    commit_url_candidate = getattr(commit_response['commit'], 'html_url', None)
                    if commit_url_candidate and BaseCommitter._validate_commit_url(commit_url_candidate):
                        commit_url = commit_url_candidate
                elif commit_response and 'commit' in commit_response and 'url' in commit_response['commit']:
                    commit_url_candidate = commit_response['commit']['url']
                    if commit_url_candidate and BaseCommitter._validate_commit_url(commit_url_candidate):
                        commit_url = commit_url_candidate
            else:
                print(f"  [AVISO] Status '{status}' não reconhecido para o arquivo '{caminho}'. Ignorando.")
        except GithubException as e:
            print(f"ERRO ao processar o arquivo '{caminho}': {e.data.get('message', str(e))}")
        except Exception as e:
            print(f"ERRO inesperado ao processar o arquivo '{caminho}': {e}")
    if commit_url and BaseCommitter._validate_commit_url(commit_url):
        resultado_branch['commit_url'] = commit_url
    else:
        resultado_branch['commit_url'] = None
    if commits_realizados > 0:
        tentativas = 0
        while tentativas < 2:
            try:
                print(f"\nCriando Pull Request de '{nome_branch}' para '{branch_alvo_do_pr}'...")
                pr = repo.create_pull(title=mensagem_pr, body=descricao_pr or "Refatoração automática gerada pela plataforma de agentes de IA.", head=nome_branch, base=branch_alvo_do_pr)
                print(f"[DEBUG][GITHUB] Tipo do objeto pr: {type(pr)}")
                print(f"[DEBUG][GITHUB] Atributos do objeto pr: {dir(pr)}")
                print(f"[DEBUG][GITHUB] pr.__dict__: {pr.__dict__}")
                print(f"[DEBUG][GITHUB] pr.html_url (direto): {getattr(pr, 'html_url', None)}")
                print(f"[DEBUG][GITHUB] pr.html_url ANTES de _finalizar_resultado_sucesso: {getattr(pr, 'html_url', 'ATRIBUTO NÃO ENCONTRADO')}")
                if not hasattr(pr, 'html_url') or pr.html_url is None or not isinstance(pr.html_url, str) or not pr.html_url.strip():
                    print(f"[ERRO][GITHUB] PR criado mas html_url inválido: {json.dumps(pr.__dict__, default=str)}")
                    BaseCommitter._finalizar_resultado_erro(resultado_branch, f"PR criado mas html_url inválido: {json.dumps(pr.__dict__, default=str)}")
                    break
                BaseCommitter._finalizar_resultado_sucesso(resultado_branch, pr.html_url.strip())
                break
            except ValueError as ve:
                print(f"[ERRO][GITHUB] Objeto PR retornado sem html_url ou html_url inválido: {getattr(pr, 'html_url', None)}")
                print(f"[ERRO][GITHUB] Detalhes do objeto PR: {pr.__dict__}")
                if tentativas == 0:
                    sufixo = _gerar_sufixo_aleatorio()
                    novo_titulo = f"{mensagem_pr}-retry-{sufixo}"
                    print(f"[GITHUB][RETRY] Tentando criar PR novamente com título modificado: {novo_titulo}")
                    mensagem_pr = novo_titulo
                    tentativas += 1
                    continue
                else:
                    raise
            except GithubException as e:
                if e.status == 422 and "A pull request for these commits already exists" in str(e.data):
                    print("AVISO: PR para esta branch já existe.")
                    try:
                        BaseCommitter._finalizar_resultado_sucesso(resultado_branch, pr_url=f"PR criado para branch: {nome_branch}", message="PR já existente.")
                    except ValueError as ve:
                        print(f"[ERRO][GITHUB] PR já existente mas pr_url inválido. Tentando retry com sufixo aleatório.")
                        sufixo = _gerar_sufixo_aleatorio()
                        novo_titulo = f"{mensagem_pr}-retry-{sufixo}"
                        mensagem_pr = novo_titulo
                        continue
                    break
                else:
                    print(f"ERRO ao criar PR para '{nome_branch}': {e}")
                    BaseCommitter._finalizar_resultado_erro(resultado_branch, f"Erro ao criar PR: {e.data.get('message', str(e))}")
                    break
            except Exception as e:
                print(f"[ERRO][GITHUB] Falha crítica ao validar PR: {e}")
                BaseCommitter._finalizar_resultado_erro(resultado_branch, f"Erro crítico ao validar PR: {e}")
                break
    else:
        print(f"\nNenhum commit realizado para a branch '{nome_branch}'. Pulando criação do PR.")
        try:
            BaseCommitter._finalizar_resultado_sucesso(resultado_branch, pr_url=f"PR criado para branch: {nome_branch}", message="Nenhuma mudança para commitar.")
        except ValueError as ve:
            print(f"[ERRO][GITHUB] PR vazio mas pr_url inválido. Tentando retry com sufixo aleatório.")
            sufixo = _gerar_sufixo_aleatorio()
            novo_titulo = f"{mensagem_pr}-retry-{sufixo}"
            mensagem_pr = novo_titulo
            BaseCommitter._finalizar_resultado_sucesso(resultado_branch, pr_url=f"PR criado para branch: {nome_branch}-{sufixo}", message="Nenhuma mudança para commitar.")
    return resultado_branch
