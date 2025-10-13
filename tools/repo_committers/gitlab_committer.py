from gitlab import exceptions as gitlab_exceptions
from typing import Dict, Any, List
from tools.repo_committers.base_committer import BaseCommitter
from tools.repo_committers.branch_name_sanitizer import BranchNameSanitizer
from tools.repo_committers.path_validator import PathValidator
import json
import random
import string

def _gerar_sufixo_aleatorio(tamanho=6):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=tamanho))

def processar_branch_gitlab(
    repo,
    nome_branch: str,
    branch_de_origem: str,
    branch_alvo_do_pr: str,
    mensagem_pr: str,
    descricao_pr: str,
    conjunto_de_mudancas: list,
    modo_adicao_incremental: bool = False
) -> Dict[str, Any]:
    print(f"\n--- Processando Lote GitLab para a Branch: '{nome_branch}' ---")
    resultado_branch = BaseCommitter._inicializar_resultado_branch(nome_branch)
    sanitized = BranchNameSanitizer.sanitize(nome_branch)
    if sanitized != nome_branch or sanitized == "invalid-branch":
        msg = f"Nome da branch inválido para GitLab: '{nome_branch}' (sanitizado: '{sanitized}')"
        print(f"[ERRO][GITLAB] {msg}")
        BaseCommitter._finalizar_resultado_erro(resultado_branch, msg)
        return resultado_branch
    try:
        BaseCommitter._validate_no_duplicate_paths(conjunto_de_mudancas)
    except ValueError as ve:
        BaseCommitter._finalizar_resultado_erro(resultado_branch, str(ve))
        return resultado_branch
    # PASSO: Garantir que a branch de destino existe ou criar explicitamente
    try:
        branches = repo.branches.list(search=nome_branch)
        branch_exists = any(b.name == nome_branch for b in branches)
        if not branch_exists:
            print(f"[GITLAB] Branch '{nome_branch}' não existe. Tentando criar a partir de '{branch_de_origem}'...")
            try:
                repo.branches.create({'branch': nome_branch, 'ref': branch_de_origem})
                print(f"[GITLAB] Branch '{nome_branch}' criada com sucesso a partir de '{branch_de_origem}'.")
            except gitlab_exceptions.GitlabCreateError as e:
                if e.response_code == 400 and 'already exists' in str(e.error_message).lower():
                    print(f"[GITLAB] Branch '{nome_branch}' já existe (race condition). Continuando...")
                else:
                    msg = f"Falha ao criar branch '{nome_branch}': {e}"
                    print(f"[ERRO][GITLAB] {msg}")
                    BaseCommitter._finalizar_resultado_erro(resultado_branch, msg)
                    return resultado_branch
        else:
            print(f"[GITLAB] Branch '{nome_branch}' já existe. Continuando...")
    except Exception as e:
        msg = f"Falha ao validar/criar branch '{nome_branch}': {e}"
        print(f"[ERRO][GITLAB] {msg}")
        BaseCommitter._finalizar_resultado_erro(resultado_branch, msg)
        return resultado_branch
    commits_realizados = 0
    commit_url = None
    mudancas_validas = BaseCommitter._processar_mudancas_comuns(conjunto_de_mudancas, resultado_branch)
    for idx, mudanca in enumerate(mudancas_validas):
        caminho = mudanca["caminho"]
        try:
            caminho_validado = PathValidator.validate_path(caminho)
        except Exception as e:
            print(f"[ERRO][GITLAB][processar_branch_gitlab] Mudança {idx}: caminho inválido: '{caminho}'. Erro: {e}")
            continue
        status = mudanca["status"]
        conteudo = mudanca["conteudo"]
        try:
            file_obj = None
            try:
                file_obj = repo.files.get(file_path=caminho_validado, ref=nome_branch)
            except Exception:
                file_obj = None
            if status in ("ADICIONADO", "CRIADO"):
                if file_obj:
                    print(f"  [AVISO] Arquivo '{caminho_validado}' marcado como ADICIONADO já existe. Será tratado como MODIFICADO.")
                    repo.files.update(file_path=caminho_validado, branch=nome_branch, content=conteudo or "", commit_message=f"refactor: {caminho_validado}")
                else:
                    repo.files.create({'file_path': caminho_validado, 'branch': nome_branch, 'content': conteudo or "", 'commit_message': f"feat: {caminho_validado}"})
                print(f"  [CRIADO/MODIFICADO] {caminho_validado}")
                commits_realizados += 1
            elif status == "MODIFICADO":
                if not file_obj:
                    print(f"  [ERRO] Arquivo '{caminho_validado}' marcado como MODIFICADO não foi encontrado na branch. Ignorando.")
                    continue
                if modo_adicao_incremental:
                    conteudo_existente = file_obj.decode().decode('utf-8') if hasattr(file_obj, 'decode') else file_obj.content
                    conteudo = BaseCommitter._mesclar_conteudo(conteudo_existente, conteudo)
                repo.files.update(file_path=caminho_validado, branch=nome_branch, content=conteudo or "", commit_message=f"refactor: {caminho_validado}")
                print(f"  [MODIFICADO] {caminho_validado}")
                commits_realizados += 1
            elif status == "REMOVIDO":
                if not file_obj:
                    print(f"  [AVISO] Arquivo '{caminho_validado}' marcado como REMOVIDO já não existe. Ignorando.")
                    continue
                repo.files.delete(file_path=caminho_validado, branch=nome_branch, commit_message=f"refactor: remove {caminho_validado}")
                print(f"  [REMOVIDO] {caminho_validado}")
                commits_realizados += 1
            else:
                print(f"  [AVISO] Status '{status}' não reconhecido para o arquivo '{caminho_validado}'. Ignorando.")
        except Exception as e:
            print(f"ERRO ao processar o arquivo '{caminho_validado}': {e}")
    if commits_realizados > 0:
        try:
            pr = repo.mergerequests.create({
                'source_branch': nome_branch,
                'target_branch': branch_alvo_do_pr,
                'title': mensagem_pr,
                'description': descricao_pr or "Refatoração automática gerada pela plataforma de agentes de IA."
            })
            pr_url = getattr(pr, 'web_url', None)
            if not pr_url or not isinstance(pr_url, str) or not pr_url.strip():
                BaseCommitter._finalizar_resultado_erro(resultado_branch, f"MR criado mas web_url inválido: {json.dumps(pr.__dict__, default=str)}")
            else:
                BaseCommitter._finalizar_resultado_sucesso(resultado_branch, pr_url.strip())
        except Exception as e:
            print(f"ERRO ao criar Merge Request para '{nome_branch}': {e}")
            BaseCommitter._finalizar_resultado_erro(resultado_branch, f"Erro ao criar MR: {e}")
    else:
        print(f"\nNenhum commit realizado para a branch '{nome_branch}'. Pulando criação do MR.")
        try:
            BaseCommitter._finalizar_resultado_sucesso(resultado_branch, pr_url=f"MR criado para branch: {nome_branch}", message="Nenhuma mudança para commitar.")
        except ValueError as ve:
            print(f"[ERRO][GITLAB] MR vazio mas pr_url inválido. Tentando retry com sufixo aleatório.")
            sufixo = _gerar_sufixo_aleatorio()
            novo_titulo = f"{mensagem_pr}-retry-{sufixo}"
            mensagem_pr = novo_titulo
            BaseCommitter._finalizar_resultado_sucesso(resultado_branch, pr_url=f"MR criado para branch: {nome_branch}-{sufixo}", message="Nenhuma mudança para commitar.")
    return resultado_branch
