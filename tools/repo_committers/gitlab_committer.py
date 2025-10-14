from typing import Dict, Any, List
from tools.repo_committers.base_committer import BaseCommitter
from tools.repo_committers.branch_name_sanitizer import BranchNameSanitizer
from tools.repo_committers.path_validator import PathValidator
import json
import random
import string

def _gerar_sufixo_aleatorio(tamanho=6):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=tamanho))

def _truncate_pr_title(title: str, max_length: int = 200) -> str:
    if title is None:
        return ""
    if len(title) > max_length:
        print(f"[gitlab_committer][WARN] Título do MR excede {max_length} caracteres. Será truncado.")
        return title[:max_length].rstrip() + "..."
    return title

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
    try:
        BaseCommitter._validate_branch_exists(repo, nome_branch, 'gitlab', branch_de_origem)
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
            arquivo_existente = None
            try:
                arquivo_existente = repo.files.get(file_path=caminho_validado, ref=nome_branch)
            except Exception:
                pass
            if status in ("ADICIONADO", "CRIADO"):
                if arquivo_existente:
                    print(f"  [AVISO] Arquivo '{caminho_validado}' marcado como ADICIONADO já existe. Será tratado como MODIFICADO.")
                    repo.files.update(file_path=caminho_validado, branch=nome_branch, content=conteudo or "", commit_message=f"refactor: {caminho_validado}")
                else:
                    repo.files.create(file_path=caminho_validado, branch=nome_branch, content=conteudo or "", commit_message=f"feat: {caminho_validado}")
                print(f"  [CRIADO/MODIFICADO] {caminho_validado}")
                commits_realizados += 1
            elif status == "MODIFICADO":
                if not arquivo_existente:
                    print(f"  [ERRO] Arquivo '{caminho_validado}' marcado como MODIFICADO não foi encontrado na branch. Ignorando.")
                    continue
                if modo_adicao_incremental:
                    conteudo_existente = arquivo_existente.decode().decode('utf-8') if hasattr(arquivo_existente, 'decode') else ""
                    conteudo = BaseCommitter._mesclar_conteudo(conteudo_existente, conteudo)
                repo.files.update(file_path=caminho_validado, branch=nome_branch, content=conteudo or "", commit_message=f"refactor: {caminho_validado}")
                print(f"  [MODIFICADO] {caminho_validado}")
                commits_realizados += 1
            elif status == "REMOVIDO":
                if not arquivo_existente:
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
        tentativas = 0
        while tentativas < 2:
            try:
                mensagem_pr_truncada = _truncate_pr_title(mensagem_pr, 200)
                print(f"\nCriando Merge Request de '{nome_branch}' para '{branch_alvo_do_pr}'...")
                mr = repo.mergerequests.create({
                    'source_branch': nome_branch,
                    'target_branch': branch_alvo_do_pr,
                    'title': mensagem_pr_truncada,
                    'description': descricao_pr or "Refatoração automática gerada pela plataforma de agentes de IA."
                })
                if not hasattr(mr, 'web_url') or mr.web_url is None or not isinstance(mr.web_url, str) or not mr.web_url.strip():
                    print(f"[ERRO][GITLAB] MR criado mas web_url inválido: {json.dumps(mr.__dict__, default=str)}")
                    BaseCommitter._finalizar_resultado_erro(resultado_branch, f"MR criado mas web_url inválido: {json.dumps(mr.__dict__, default=str)}")
                    break
                BaseCommitter._finalizar_resultado_sucesso(resultado_branch, mr.web_url.strip())
                break
            except ValueError as ve:
                print(f"[ERRO][GITLAB] Objeto MR retornado sem web_url ou web_url inválido: {getattr(mr, 'web_url', None)}")
                print(f"[ERRO][GITLAB] Detalhes do objeto MR: {mr.__dict__}")
                if tentativas == 0:
                    sufixo = _gerar_sufixo_aleatorio()
                    novo_titulo = f"{mensagem_pr}-retry-{sufixo}"
                    mensagem_pr = novo_titulo
                    continue
                else:
                    raise
            except Exception as e:
                print(f"ERRO ao criar MR para '{nome_branch}': {e}")
                BaseCommitter._finalizar_resultado_erro(resultado_branch, f"Erro ao criar MR: {str(e)}")
                break
    else:
        print(f"\nNenhum commit realizado para a branch '{nome_branch}'. Pulando criação do MR.")
        try:
            mensagem_pr_truncada = _truncate_pr_title(mensagem_pr, 200)
            BaseCommitter._finalizar_resultado_sucesso(resultado_branch, pr_url=f"MR criado para branch: {nome_branch}", message="Nenhuma mudança para commitar.")
        except ValueError as ve:
            print(f"[ERRO][GITLAB] MR vazio mas pr_url inválido. Tentando retry com sufixo aleatório.")
            sufixo = _gerar_sufixo_aleatorio()
            novo_titulo = f"{mensagem_pr}-retry-{sufixo}"
            mensagem_pr = novo_titulo
            BaseCommitter._finalizar_resultado_sucesso(resultado_branch, pr_url=f"MR criado para branch: {nome_branch}-{sufixo}", message="Nenhuma mudança para commitar.")
    return resultado_branch
