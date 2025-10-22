from typing import Dict, Any, List
from tools.repo_committers.base_committer import BaseCommitter
from tools.repo_committers.branch_name_sanitizer import BranchNameSanitizer
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
    conjunto_de_mudancas: list
) -> Dict[str, Any]:
    resultado_branch = BaseCommitter._inicializar_resultado_branch(nome_branch)
    sanitized = BranchNameSanitizer.sanitize(nome_branch)
    if sanitized != nome_branch or sanitized == "invalid-branch":
        msg = f"Nome da branch inválido para GitLab: '{nome_branch}' (sanitizado: '{sanitized}')"
        BaseCommitter._finalizar_resultado_erro(resultado_branch, msg)
        return resultado_branch
    valid, error_msg = BaseCommitter._validate_files_exist_in_source(conjunto_de_mudancas, repo, branch_de_origem, 'gitlab')
    if not valid:
        BaseCommitter._finalizar_resultado_erro(resultado_branch, error_msg)
        return resultado_branch
    try:
        BaseCommitter._validate_no_duplicate_paths(conjunto_de_mudancas)
    except ValueError as ve:
        BaseCommitter._finalizar_resultado_erro(resultado_branch, str(ve))
        return resultado_branch
    commits_realizados = 0
    last_commit_id = None
    try:
        try:
            repo.branches.create({'branch': nome_branch, 'ref': branch_de_origem})
        except Exception as e:
            if "already exists" in str(e).lower():
                pass
            else:
                raise
        mudancas_validas = BaseCommitter._processar_mudancas_comuns(conjunto_de_mudancas, resultado_branch)
        for i, mudanca in enumerate(mudancas_validas):
            caminho = mudanca["caminho"]
            status = mudanca["status"]
            conteudo = mudanca["conteudo"]
            commit_id = None
            if status == "MODIFICADO":
                try:
                    arquivo = repo.files.get(file_path=caminho, ref=nome_branch)
                except Exception:
                    continue
            try:
                if status in ("ADICIONADO", "CRIADO"):
                    dados_criacao = {
                        'file_path': caminho,
                        'branch': nome_branch,
                        'content': conteudo or "",
                        'commit_message': f"feat: Cria {caminho}"
                    }
                    file_obj = repo.files.create(dados_criacao)
                    commits_realizados += 1
                    if hasattr(file_obj, 'commit_id'):
                        commit_id = getattr(file_obj, 'commit_id', None)
                elif status == "MODIFICADO":
                    arquivo = repo.files.get(file_path=caminho, ref=nome_branch)
                    conteudo_existente = arquivo.decode().decode('utf-8') if hasattr(arquivo, 'decode') else arquivo.content
                    arquivo.content = conteudo or ""
                    arquivo.save(branch=nome_branch, commit_message=f"refactor: Modifica {caminho}")
                    commits_realizados += 1
                    if hasattr(arquivo, 'commit_id'):
                        commit_id = getattr(arquivo, 'commit_id', None)
                elif status == "REMOVIDO":
                    delete_result = repo.files.delete(file_path=caminho,
                                      branch=nome_branch,
                                      commit_message=f"refactor: Remove {caminho}")
                    commits_realizados += 1
                    if isinstance(delete_result, dict) and 'commit_id' in delete_result:
                        commit_id = delete_result['commit_id']
                if commit_id:
                    last_commit_id = commit_id
            except Exception as file_e:
                pass
        if last_commit_id:
            repo_web_url = getattr(repo, 'web_url', None)
            commit_url_candidate = f"{repo_web_url}/-/commit/{last_commit_id}" if repo_web_url and last_commit_id else None
            if commit_url_candidate and BaseCommitter._validate_commit_url(commit_url_candidate):
                resultado_branch['commit_url'] = commit_url_candidate
            else:
                resultado_branch['commit_url'] = None
        if commits_realizados > 0:
            tentativas = 0
            while tentativas < 2:
                try:
                    mr_result = repo.mergerequests.create({
                        'source_branch': nome_branch,
                        'target_branch': branch_alvo_do_pr,
                        'title': mensagem_pr,
                        'description': descricao_pr or "Refatoração automática gerada pela plataforma de agentes de IA."
                    })
                    if not hasattr(mr_result, 'web_url') or mr_result.web_url is None or not isinstance(mr_result.web_url, str) or not mr_result.web_url.strip():
                        BaseCommitter._finalizar_resultado_erro(resultado_branch, f"MR criado mas web_url inválido: {json.dumps(mr_result.__dict__, default=str)}")
                        break
                    BaseCommitter._finalizar_resultado_sucesso(resultado_branch, mr_result.web_url.strip())
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
                except Exception as mr_e:
                    if "already exists" in str(mr_e).lower():
                        mrs = repo.mergerequests.list(state='opened', source_branch=nome_branch, target_branch=branch_alvo_do_pr)
                        mr_url = mrs[0].web_url if mrs else "URL não encontrada"
                        try:
                            BaseCommitter._finalizar_resultado_sucesso(resultado_branch, mr_url, "MR já existente.")
                        except ValueError as ve:
                            sufixo = _gerar_sufixo_aleatorio()
                            novo_titulo = f"{mensagem_pr}-retry-{sufixo}"
                            mensagem_pr = novo_titulo
                            continue
                        break
                    else:
                        BaseCommitter._finalizar_resultado_erro(resultado_branch, f"Erro ao criar MR: {mr_e}")
                        break
        else:
            try:
                BaseCommitter._finalizar_resultado_sucesso(resultado_branch, pr_url=f"MR criado para branch: {nome_branch}", message="Nenhuma mudança para commitar.")
            except ValueError as ve:
                sufixo = _gerar_sufixo_aleatorio()
                novo_titulo = f"{mensagem_pr}-retry-{sufixo}"
                mensagem_pr = novo_titulo
                BaseCommitter._finalizar_resultado_sucesso(resultado_branch, pr_url=f"MR criado para branch: {nome_branch}-{sufixo}", message="Nenhuma mudança para commitar.")
    except Exception as e:
        BaseCommitter._finalizar_resultado_erro(resultado_branch, f"Erro fatal: {e}")
    return resultado_branch
