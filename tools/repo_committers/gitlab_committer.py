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
    conjunto_de_mudancas: list,
    modo_adicao_incremental: bool = False
) -> Dict[str, Any]:
    print(f"\n--- Processando Lote GitLab para a Branch: '{nome_branch}' ---")
    print(f"[DEBUG][GITLAB] Tipo do objeto repo: {type(repo)}")
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
    commits_realizados = 0
    last_commit_id = None
    try:
        print(f"[DEBUG][GITLAB] Iniciando criação da branch: {nome_branch} a partir de {branch_de_origem}")
        try:
            print(f"[DEBUG][GITLAB] Chamando repo.branches.create com parâmetros: {{'branch': '{nome_branch}', 'ref': '{branch_de_origem}'}}")
            repo.branches.create({'branch': nome_branch, 'ref': branch_de_origem})
            print(f"[DEBUG][GITLAB] Branch GitLab '{nome_branch}' criada com sucesso.")
        except Exception as e:
            print(f"[DEBUG][GITLAB] Exceção ao criar branch: {type(e).__name__}: {str(e)}")
            if "already exists" in str(e).lower():
                print(f"AVISO: A branch GitLab '{nome_branch}' já existe. Commits serão adicionados a ela.")
            else:
                print(f"[ERRO][GITLAB] Falha crítica ao criar branch: {e}")
                raise
        print(f"[DEBUG][GITLAB] Iniciando aplicação de {len(conjunto_de_mudancas)} mudanças no GitLab...")
        mudancas_validas = BaseCommitter._processar_mudancas_comuns(conjunto_de_mudancas, resultado_branch)
        for i, mudanca in enumerate(mudancas_validas):
            print(f"[DEBUG][GITLAB] Processando mudança {i+1}/{len(mudancas_validas)}")
            caminho = mudanca["caminho"]
            status = mudanca["status"]
            conteudo = mudanca["conteudo"]
            print(f"[DEBUG][GITLAB] Mudança: arquivo='{caminho}', status='{status}', conteudo_length={len(conteudo) if conteudo else 0}")
            try:
                commit_id = None
                if status in ("ADICIONADO", "CRIADO"):
                    print(f"[DEBUG][GITLAB] Chamando repo.files.create para {caminho}")
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
                    print(f"[DEBUG][GITLAB] Buscando arquivo para modificar: {caminho}")
                    arquivo = repo.files.get(file_path=caminho, ref=nome_branch)
                    conteudo_existente = arquivo.decode().decode('utf-8') if hasattr(arquivo, 'decode') else arquivo.content
                    if modo_adicao_incremental:
                        conteudo = BaseCommitter._mesclar_conteudo(conteudo_existente, conteudo)
                    arquivo.content = conteudo or ""
                    arquivo.save(branch=nome_branch, commit_message=f"refactor: Modifica {caminho}")
                    commits_realizados += 1
                    if hasattr(arquivo, 'commit_id'):
                        commit_id = getattr(arquivo, 'commit_id', None)
                elif status == "REMOVIDO":
                    print(f"[DEBUG][GITLAB] Chamando repo.files.delete para {caminho}")
                    delete_result = repo.files.delete(file_path=caminho,
                                      branch=nome_branch,
                                      commit_message=f"refactor: Remove {caminho}")
                    commits_realizados += 1
                    if isinstance(delete_result, dict) and 'commit_id' in delete_result:
                        commit_id = delete_result['commit_id']
                else:
                    print(f"  [AVISO] Status '{status}' não reconhecido para o arquivo GitLab '{caminho}'. Ignorando.")
                if commit_id:
                    last_commit_id = commit_id
            except Exception as file_e:
                print(f"[ERRO][GITLAB] Erro ao processar o arquivo '{caminho}': {type(file_e).__name__}: {file_e}")
                import traceback
                traceback.print_exc()
        if last_commit_id:
            repo_web_url = getattr(repo, 'web_url', None)
            if repo_web_url:
                resultado_branch['commit_url'] = f"{repo_web_url}/-/commit/{last_commit_id}"
            else:
                resultado_branch['commit_url'] = None
        print(f"[DEBUG][GITLAB] Commits realizados: {commits_realizados}")
        if commits_realizados > 0:
            tentativas = 0
            while tentativas < 2:
                try:
                    print(f"\n[DEBUG][GITLAB] Criando Merge Request de '{nome_branch}' para '{branch_alvo_do_pr}'...")
                    mr_result = repo.mergerequests.create({
                        'source_branch': nome_branch,
                        'target_branch': branch_alvo_do_pr,
                        'title': mensagem_pr,
                        'description': descricao_pr or "Refatoração automática gerada pela plataforma de agentes de IA."
                    })
                    print(f"[DEBUG][GITLAB] Tipo do objeto mr_result: {type(mr_result)}")
                    print(f"[DEBUG][GITLAB] Atributos do objeto mr_result: {dir(mr_result)}")
                    print(f"[DEBUG][GITLAB] mr_result.__dict__: {mr_result.__dict__}")
                    print(f"[DEBUG][GITLAB] mr_result.web_url (direto): {getattr(mr_result, 'web_url', None)}")
                    print(f"[DEBUG][GITLAB] mr_result.web_url ANTES de validação: {getattr(mr_result, 'web_url', 'ATRIBUTO NÃO ENCONTRADO')}")
                    if not hasattr(mr_result, 'web_url') or mr_result.web_url is None or not isinstance(mr_result.web_url, str) or not mr_result.web_url.strip():
                        print(f"[ERRO][GITLAB] MR criado mas web_url inválido: {json.dumps(mr_result.__dict__, default=str)}")
                        BaseCommitter._finalizar_resultado_erro(resultado_branch, f"MR criado mas web_url inválido: {json.dumps(mr_result.__dict__, default=str)}")
                        break
                    BaseCommitter._finalizar_resultado_sucesso(resultado_branch, mr_result.web_url.strip())
                    break
                except ValueError as ve:
                    print(f"[ERRO][GITLAB] Objeto MR retornado sem web_url ou web_url inválido: {getattr(mr_result, 'web_url', None)}")
                    print(f"[ERRO][GITLAB] Detalhes do objeto MR: {mr_result.__dict__}")
                    if tentativas == 0:
                        sufixo = _gerar_sufixo_aleatorio()
                        novo_titulo = f"{mensagem_pr}-retry-{sufixo}"
                        print(f"[GITLAB][RETRY] Tentando criar MR novamente com título modificado: {novo_titulo}")
                        mensagem_pr = novo_titulo
                        tentativas += 1
                        continue
                    else:
                        raise
                except Exception as mr_e:
                    print(f"[ERRO][GITLAB] Exceção ao criar MR: {type(mr_e).__name__}: {mr_e}")
                    if "already exists" in str(mr_e).lower():
                        mrs = repo.mergerequests.list(state='opened', source_branch=nome_branch, target_branch=branch_alvo_do_pr)
                        mr_url = mrs[0].web_url if mrs else "URL não encontrada"
                        print(f"AVISO: MR para esta branch GitLab já existe. URL: {mr_url}")
                        try:
                            BaseCommitter._finalizar_resultado_sucesso(resultado_branch, mr_url, "MR já existente.")
                        except ValueError as ve:
                            print(f"[ERRO][GITLAB] MR já existente mas web_url inválido. Tentando retry com sufixo aleatório.")
                            sufixo = _gerar_sufixo_aleatorio()
                            novo_titulo = f"{mensagem_pr}-retry-{sufixo}"
                            mensagem_pr = novo_titulo
                            continue
                        break
                    else:
                        print(f"ERRO ao criar MR GitLab para '{nome_branch}': {mr_e}")
                        BaseCommitter._finalizar_resultado_erro(resultado_branch, f"Erro ao criar MR: {mr_e}")
                        break
        else:
            print(f"\nNenhum commit realizado para a branch GitLab '{nome_branch}'. Pulando criação do MR.")
            try:
                BaseCommitter._finalizar_resultado_sucesso(resultado_branch, pr_url=f"MR criado para branch: {nome_branch}", message="Nenhuma mudança para commitar.")
            except ValueError as ve:
                print(f"[ERRO][GITLAB] MR vazio mas web_url inválido. Tentando retry com sufixo aleatório.")
                sufixo = _gerar_sufixo_aleatorio()
                novo_titulo = f"{mensagem_pr}-retry-{sufixo}"
                mensagem_pr = novo_titulo
                BaseCommitter._finalizar_resultado_sucesso(resultado_branch, pr_url=f"MR criado para branch: {nome_branch}-{sufixo}", message="Nenhuma mudança para commitar.")
    except Exception as e:
        print(f"[ERRO][GITLAB] ERRO FATAL ao processar branch GitLab '{nome_branch}': {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        BaseCommitter._finalizar_resultado_erro(resultado_branch, f"Erro fatal: {e}")
    print(f"[DEBUG][GITLAB] Resultado final da branch {nome_branch}: {resultado_branch}")
    return resultado_branch
