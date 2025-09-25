from typing import Dict, Any, List
from tools.repo_committers.base_committer import BaseCommitter

def processar_branch_gitlab(
    repo,
    nome_branch: str,
    branch_de_origem: str,
    branch_alvo_do_pr: str,
    mensagem_pr: str,
    descricao_pr: str,
    conjunto_de_mudancas: list
) -> Dict[str, Any]:
    print(f"\n--- Processando Lote GitLab para a Branch: '{nome_branch}' ---")
    print(f"[DEBUG][GITLAB] Tipo do objeto repo: {type(repo)}")
    
    resultado_branch = BaseCommitter._inicializar_resultado_branch(nome_branch)
    commits_realizados = 0

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
                if status in ("ADICIONADO", "CRIADO"):
                    print(f"[DEBUG][GITLAB] Chamando repo.files.create para {caminho}")
                    dados_criacao = {
                        'file_path': caminho,
                        'branch': nome_branch,
                        'content': conteudo or "",
                        'commit_message': f"feat: Cria {caminho}"
                    }
                    repo.files.create(dados_criacao)
                    print(f"  [CRIADO] GitLab {caminho}")
                    commits_realizados += 1

                elif status == "MODIFICADO":
                    print(f"[DEBUG][GITLAB] Buscando arquivo para modificar: {caminho}")
                    arquivo = repo.files.get(file_path=caminho, ref=nome_branch)
                    arquivo.content = conteudo or ""
                    arquivo.save(branch=nome_branch, commit_message=f"refactor: Modifica {caminho}")
                    print(f"  [MODIFICADO] GitLab {caminho}")
                    commits_realizados += 1

                elif status == "REMOVIDO":
                    print(f"[DEBUG][GITLAB] Chamando repo.files.delete para {caminho}")
                    repo.files.delete(file_path=caminho,
                                      branch=nome_branch,
                                      commit_message=f"refactor: Remove {caminho}")
                    print(f"  [REMOVIDO] GitLab {caminho}")
                    commits_realizados += 1
                
                else:
                    print(f"  [AVISO] Status '{status}' não reconhecido para o arquivo GitLab '{caminho}'. Ignorando.")

            except Exception as file_e:
                print(f"[ERRO][GITLAB] Erro ao processar o arquivo '{caminho}': {type(file_e).__name__}: {file_e}")
                import traceback
                traceback.print_exc()
            
        print(f"[DEBUG][GITLAB] Commits realizados: {commits_realizados}")
        if commits_realizados > 0:
            try:
                print(f"\n[DEBUG][GITLAB] Criando Merge Request de '{nome_branch}' para '{branch_alvo_do_pr}'...")
                mr_result = repo.mergerequests.create({
                    'source_branch': nome_branch,
                    'target_branch': branch_alvo_do_pr,
                    'title': mensagem_pr,
                    'description': descricao_pr or "Refatoração automática gerada pela plataforma de agentes de IA."
                })
                mr_url = getattr(mr_result, 'web_url', 'URL não disponível')
                print(f"Merge Request GitLab criado com sucesso! URL: {mr_url}")
                BaseCommitter._finalizar_resultado_sucesso(resultado_branch, mr_url)
                
            except Exception as mr_e:
                print(f"[ERRO][GITLAB] Exceção ao criar MR: {type(mr_e).__name__}: {mr_e}")
                if "already exists" in str(mr_e).lower():
                    mrs = repo.mergerequests.list(state='opened', source_branch=nome_branch, target_branch=branch_alvo_do_pr)
                    mr_url = mrs[0].web_url if mrs else "URL não encontrada"
                    print(f"AVISO: MR para esta branch GitLab já existe. URL: {mr_url}")
                    BaseCommitter._finalizar_resultado_sucesso(resultado_branch, mr_url, "MR já existente.")
                else:
                    print(f"ERRO ao criar MR GitLab para '{nome_branch}': {mr_e}")
                    BaseCommitter._finalizar_resultado_erro(resultado_branch, f"Erro ao criar MR: {mr_e}")
        else:
            print(f"\nNenhum commit realizado para a branch GitLab '{nome_branch}'. Pulando criação do MR.")
            BaseCommitter._finalizar_resultado_sucesso(resultado_branch, message="Nenhuma mudança para commitar.")

    except Exception as e:
        print(f"[ERRO][GITLAB] ERRO FATAL ao processar branch GitLab '{nome_branch}': {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        BaseCommitter._finalizar_resultado_erro(resultado_branch, f"Erro fatal: {e}")

    print(f"[DEBUG][GITLAB] Resultado final da branch {nome_branch}: {resultado_branch}")
    return resultado_branch