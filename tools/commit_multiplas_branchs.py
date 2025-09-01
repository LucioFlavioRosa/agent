import json
from github import GithubException, UnknownObjectException
from tools.github_connector import GitHubConnector
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.github_repository_provider import GitHubRepositoryProvider
from typing import Dict, Any, List, Optional

def _is_gitlab_project(repo) -> bool:
    return hasattr(repo, 'web_url') or 'gitlab' in str(type(repo)).lower()

def _processar_uma_branch_gitlab(
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
    print(f"[DEBUG][GITLAB] Atributos disponíveis: {[attr for attr in dir(repo) if not attr.startswith('_')][:10]}...")
    
    resultado_branch = {
        "branch_name": nome_branch,
        "success": False,
        "pr_url": None,
        "message": "",
        "arquivos_modificados": []
    }
    commits_realizados = 0

    try:
        # ETAPA 1: Criação da branch no GitLab
        print(f"[DEBUG][GITLAB] Iniciando criação da branch: {nome_branch} a partir de {branch_de_origem}")
        try:
            print(f"[DEBUG][GITLAB] Chamando repo.branches.create com parâmetros: {{'branch': '{nome_branch}', 'ref': '{branch_de_origem}'}}")
            result = repo.branches.create({'branch': nome_branch, 'ref': branch_de_origem})
            print(f"[DEBUG][GITLAB] Branch GitLab '{nome_branch}' criada com sucesso. Resultado: {result}")
        except Exception as e:
            print(f"[DEBUG][GITLAB] Exceção ao criar branch: {type(e).__name__}: {str(e)}")
            if "already exists" in str(e).lower():
                print(f"AVISO: A branch GitLab '{nome_branch}' já existe. Commits serão adicionados a ela.")
            else:
                print(f"[ERRO][GITLAB] Falha crítica ao criar branch: {e}")
                raise

        # ETAPA 2: Aplicação das mudanças no GitLab
        print(f"[DEBUG][GITLAB] Iniciando aplicação de {len(conjunto_de_mudancas)} mudanças no GitLab...")
        
        for i, mudanca in enumerate(conjunto_de_mudancas):
            print(f"[DEBUG][GITLAB] Processando mudança {i+1}/{len(conjunto_de_mudancas)}")
            caminho = mudanca.get("caminho_do_arquivo")
            status = mudanca.get("status", "").upper()
            conteudo = mudanca.get("conteudo")
            justificativa = mudanca.get("justificativa", f"Aplicando mudança em {caminho}")

            print(f"[DEBUG][GITLAB] Mudança: arquivo='{caminho}', status='{status}', conteudo_length={len(conteudo) if conteudo else 0}")

            if not caminho:
                print("  [AVISO] Mudança ignorada por não ter 'caminho_do_arquivo'.")
                continue

            try:
                # Verificação de existência do arquivo no GitLab
                print(f"[DEBUG][GITLAB] Verificando existência do arquivo: {caminho}")
                arquivo_existe = False
                try:
                    file_result = repo.files.get(file_path=caminho, ref=nome_branch)
                    arquivo_existe = True
                    print(f"[DEBUG][GITLAB] Arquivo {caminho} existe na branch {nome_branch}")
                except Exception as check_e:
                    arquivo_existe = False
                    print(f"[DEBUG][GITLAB] Arquivo {caminho} não existe na branch {nome_branch}: {check_e}")

                # Processamento por status no GitLab
                if status in ("ADICIONADO", "CRIADO"):
                    if arquivo_existe:
                        print(f"  [AVISO] Arquivo GitLab '{caminho}' marcado como ADICIONADO já existe. Será tratado como MODIFICADO.")
                        print(f"[DEBUG][GITLAB] Chamando repo.files.update para {caminho}")
                        update_result = repo.files.update({
                            'file_path': caminho,
                            'branch': nome_branch,
                            'content': conteudo,
                            'commit_message': f"refactor: {caminho}"
                        })
                        print(f"[DEBUG][GITLAB] Update result: {update_result}")
                    else:
                        print(f"[DEBUG][GITLAB] Chamando repo.files.create para {caminho}")
                        create_result = repo.files.create({
                            'file_path': caminho,
                            'branch': nome_branch,
                            'content': conteudo,
                            'commit_message': f"feat: {caminho}"
                        })
                        print(f"[DEBUG][GITLAB] Create result: {create_result}")
                    
                    print(f"  [CRIADO/MODIFICADO] GitLab {caminho}")
                    commits_realizados += 1
                    resultado_branch["arquivos_modificados"].append(caminho)

                elif status == "MODIFICADO":
                    if not arquivo_existe:
                        print(f"  [ERRO] Arquivo GitLab '{caminho}' marcado como MODIFICADO não foi encontrado na branch. Ignorando.")
                        continue
                    
                    print(f"[DEBUG][GITLAB] Chamando repo.files.update para modificar {caminho}")
                    update_result = repo.files.update({
                        'file_path': caminho,
                        'branch': nome_branch,
                        'content': conteudo,
                        'commit_message': f"refactor: {caminho}"
                    })
                    print(f"[DEBUG][GITLAB] Update result: {update_result}")
                    print(f"  [MODIFICADO] GitLab {caminho}")
                    commits_realizados += 1
                    resultado_branch["arquivos_modificados"].append(caminho)

                elif status == "REMOVIDO":
                    if not arquivo_existe:
                        print(f"  [AVISO] Arquivo GitLab '{caminho}' marcado como REMOVIDO já não existe. Ignorando.")
                        continue
                    
                    print(f"[DEBUG][GITLAB] Chamando repo.files.delete para {caminho}")
                    delete_result = repo.files.delete({
                        'file_path': caminho,
                        'branch': nome_branch,
                        'commit_message': f"refactor: remove {caminho}"
                    })
                    print(f"[DEBUG][GITLAB] Delete result: {delete_result}")
                    print(f"  [REMOVIDO] GitLab {caminho}")
                    commits_realizados += 1
                    resultado_branch["arquivos_modificados"].append(caminho)
                
                else:
                    print(f"  [AVISO] Status '{status}' não reconhecido para o arquivo GitLab '{caminho}'. Ignorando.")

            except Exception as file_e:
                print(f"[ERRO][GITLAB] Erro ao processar o arquivo '{caminho}': {type(file_e).__name__}: {file_e}")
                import traceback
                traceback.print_exc()
            
        # ETAPA 3: Criação do Merge Request no GitLab
        print(f"[DEBUG][GITLAB] Commits realizados: {commits_realizados}")
        if commits_realizados > 0:
            try:
                print(f"\n[DEBUG][GITLAB] Criando Merge Request de '{nome_branch}' para '{branch_alvo_do_pr}'...")
                print(f"[DEBUG][GITLAB] Parâmetros do MR: source_branch='{nome_branch}', target_branch='{branch_alvo_do_pr}', title='{mensagem_pr}'")
                
                mr_result = repo.mergerequests.create({
                    'source_branch': nome_branch,
                    'target_branch': branch_alvo_do_pr,
                    'title': mensagem_pr,
                    'description': descricao_pr
                })
                print(f"[DEBUG][GITLAB] MR criado com sucesso! Resultado: {mr_result}")
                mr_url = getattr(mr_result, 'web_url', 'URL não disponível')
                print(f"Merge Request GitLab criado com sucesso! URL: {mr_url}")
                resultado_branch.update({"success": True, "pr_url": mr_url, "message": "MR criado."})
                
            except Exception as mr_e:
                print(f"[ERRO][GITLAB] Exceção ao criar MR: {type(mr_e).__name__}: {mr_e}")
                if "already exists" in str(mr_e).lower():
                    print("AVISO: MR para esta branch GitLab já existe.")
                    resultado_branch.update({"success": True, "message": "MR já existente."})
                else:
                    print(f"ERRO ao criar MR GitLab para '{nome_branch}': {mr_e}")
                    resultado_branch["message"] = f"Erro ao criar MR: {mr_e}"
                    import traceback
                    traceback.print_exc()
        else:
            print(f"\nNenhum commit realizado para a branch GitLab '{nome_branch}'. Pulando criação do MR.")
            resultado_branch.update({"success": True, "message": "Nenhuma mudança para commitar."})

    except Exception as e:
        print(f"[ERRO][GITLAB] ERRO FATAL ao processar branch GitLab '{nome_branch}': {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        resultado_branch["message"] = f"Erro fatal: {e}"

    print(f"[DEBUG][GITLAB] Resultado final da branch {nome_branch}: {resultado_branch}")
    return resultado_branch

def _processar_uma_branch(
    repo,
    nome_branch: str,
    branch_de_origem: str,
    branch_alvo_do_pr: str,
    mensagem_pr: str,
    descricao_pr: str,
    conjunto_de_mudancas: list
) -> Dict[str, Any]:
    # Detecção do tipo de repositório e delegação para fluxo específico
    if _is_gitlab_project(repo):
        print(f"[DEBUG] Detectado repositório GitLab, delegando para fluxo específico")
        return _processar_uma_branch_gitlab(
            repo, nome_branch, branch_de_origem, branch_alvo_do_pr,
            mensagem_pr, descricao_pr, conjunto_de_mudancas
        )
    
    # Fluxo original do GitHub (mantido inalterado)
    print(f"\n--- Processando Lote para a Branch: '{nome_branch}' ---")
    
    resultado_branch = {
        "branch_name": nome_branch,
        "success": False,
        "pr_url": None,
        "message": "",
        "arquivos_modificados": []
    }
    commits_realizados = 0

    try:
        # ETAPA 1: Criação da branch empilhada
        # Tenta criar nova branch a partir da branch de origem (estratégia de empilhamento)
        ref_base = repo.get_git_ref(f"heads/{branch_de_origem}")
        repo.create_git_ref(ref=f"refs/heads/{nome_branch}", sha=ref_base.object.sha)
        print(f"Branch '{nome_branch}' criada a partir de '{branch_de_origem}'.")
        
    except GithubException as e:
        # Tratamento específico: branch já existe (cenário comum em re-execuções)
        if e.status == 422 and "Reference already exists" in str(e.data):
            print(f"AVISO: A branch '{nome_branch}' já existe. Commits serão adicionados a ela.")
        else:
            raise

    # ETAPA 2: Aplicação sequencial das mudanças
    print(f"Iniciando aplicação de {len(conjunto_de_mudancas)} mudanças...")
    
    for mudanca in conjunto_de_mudancas:
        # Extração dos dados da mudança
        caminho = mudanca.get("caminho_do_arquivo")
        status = mudanca.get("status", "").upper()
        conteudo = mudanca.get("conteudo")
        justificativa = mudanca.get("justificativa", f"Aplicando mudança em {caminho}")

        # Validação básica: mudanças sem caminho são ignoradas
        if not caminho:
            print("  [AVISO] Mudança ignorada por não ter 'caminho_do_arquivo'.")
            continue

        try:
            # ETAPA 2.1: Verificação de existência do arquivo
            # Determina se arquivo já existe na branch para escolher operação apropriada
            sha_arquivo_existente = None
            try:
                arquivo_existente = repo.get_contents(caminho, ref=nome_branch)
                sha_arquivo_existente = arquivo_existente.sha
            except UnknownObjectException:
                # Arquivo não existe - será tratado como criação
                pass

            # ETAPA 2.2: Processamento diferenciado por status
            # Cada tipo de mudança requer operação específica na API
            
            if status in ("ADICIONADO", "CRIADO"):
                # Caso especial: arquivo marcado como ADICIONADO mas já existe
                # Isso pode acontecer em re-execuções ou inconsistências de dados
                if sha_arquivo_existente:
                    print(f"  [AVISO] Arquivo '{caminho}' marcado como ADICIONADO já existe. Será tratado como MODIFICADO.")
                    repo.update_file(path=caminho, message=f"refactor: {caminho}", content=conteudo, sha=sha_arquivo_existente, branch=nome_branch)
                else:
                    # Criação normal de novo arquivo
                    repo.create_file(path=caminho, message=f"feat: {caminho}", content=conteudo, branch=nome_branch)
                    
                print(f"  [CRIADO/MODIFICADO] {caminho}")
                commits_realizados += 1
                resultado_branch["arquivos_modificados"].append(caminho)

            elif status == "MODIFICADO":
                # Validação: arquivo deve existir para ser modificado
                if not sha_arquivo_existente:
                    print(f"  [ERRO] Arquivo '{caminho}' marcado como MODIFICADO não foi encontrado na branch. Ignorando.")
                    continue
                    
                # Atualização do arquivo existente usando SHA para controle de versão
                repo.update_file(path=caminho, message=f"refactor: {caminho}", content=conteudo, sha=sha_arquivo_existente, branch=nome_branch)
                print(f"  [MODIFICADO] {caminho}")
                commits_realizados += 1
                resultado_branch["arquivos_modificados"].append(caminho)

            elif status == "REMOVIDO":
                # Validação: arquivo deve existir para ser removido
                if not sha_arquivo_existente:
                    print(f"  [AVISO] Arquivo '{caminho}' marcado como REMOVIDO já não existe. Ignorando.")
                    continue
                    
                # Remoção do arquivo usando SHA para identificação precisa
                repo.delete_file(path=caminho, message=f"refactor: remove {caminho}", sha=sha_arquivo_existente, branch=nome_branch)
                print(f"  [REMOVIDO] {caminho}")
                commits_realizados += 1
                resultado_branch["arquivos_modificados"].append(caminho)
            
            else:
                # Status não reconhecido - log de aviso sem interromper processamento
                print(f"  [AVISO] Status '{status}' não reconhecido para o arquivo '{caminho}'. Ignorando.")

        except GithubException as e:
            # Tratamento de erros específicos da API
            print(f"ERRO ao processar o arquivo '{caminho}': {e.data.get('message', str(e))}")
        except Exception as e:
            # Tratamento de erros inesperados
            print(f"ERRO inesperado ao processar o arquivo '{caminho}': {e}")
            
    # ETAPA 3: Criação do Pull Request (apenas se houve mudanças)
    if commits_realizados > 0:
        try:
            print(f"\nCriando Pull Request de '{nome_branch}' para '{branch_alvo_do_pr}'...")
            
            # Criação do PR seguindo estratégia de empilhamento
            # head=nome_branch (branch com mudanças), base=branch_alvo_do_pr (branch anterior)
            pr = repo.create_pull(title=mensagem_pr, body=descricao_pr, head=nome_branch, base=branch_alvo_do_pr)
            print(f"Pull Request criado com sucesso! URL: {pr.html_url}")
            resultado_branch.update({"success": True, "pr_url": pr.html_url, "message": "PR criado."})
            
        except GithubException as e:
            # Tratamento específico: PR já existe para esta branch
            if e.status == 422 and "A pull request for these commits already exists" in str(e.data):
                print("AVISO: PR para esta branch já existe.")
                resultado_branch.update({"success": True, "message": "PR já existente."})
            else:
                print(f"ERRO ao criar PR para '{nome_branch}': {e}")
                resultado_branch["message"] = f"Erro ao criar PR: {e.data.get('message', str(e))}"
    else:
        # Nenhum commit realizado - sucesso sem PR
        print(f"\nNenhum commit realizado para a branch '{nome_branch}'. Pulando criação do PR.")
        resultado_branch.update({"success": True, "message": "Nenhuma mudança para commitar."})

    return resultado_branch


def processar_e_subir_mudancas_agrupadas(
    nome_repo: str,
    dados_agrupados: dict,
    base_branch: str = "main",
    repository_provider: Optional[IRepositoryProvider] = None
) -> List[Dict[str, Any]]:
    print(f"[DEBUG] ENTRADA processar_e_subir_mudancas_agrupadas:")
    print(f"[DEBUG]   nome_repo: {nome_repo}")
    print(f"[DEBUG]   base_branch: {base_branch}")
    print(f"[DEBUG]   repository_provider: {type(repository_provider).__name__ if repository_provider else None}")
    print(f"[DEBUG]   dados_agrupados keys: {list(dados_agrupados.keys()) if dados_agrupados else 'None'}")
    print(f"[DEBUG]   número de grupos: {len(dados_agrupados.get('grupos', []))}")
    
    resultados_finais = []
    
    try:
        provider_name = type(repository_provider).__name__ if repository_provider else "GitHubRepositoryProvider (padrão)"
        print(f"--- Iniciando o Processo de Pull Requests Empilhados via {provider_name} ---")
        
        # ETAPA 1: Inicialização das dependências
        # Usa o provedor injetado ou cria um com dependências padrão
        if repository_provider is None:
            repository_provider = GitHubRepositoryProvider()
            print("AVISO: Nenhum provedor especificado. Usando GitHubRepositoryProvider como padrão.")
        
        print(f"[DEBUG] Criando GitHubConnector com provider: {type(repository_provider).__name__}")
        connector = GitHubConnector(repository_provider=repository_provider)
        
        print(f"[DEBUG] Estabelecendo conexão com repositório: {nome_repo}")
        repo = connector.connection(repositorio=nome_repo)
        print(f"[DEBUG] Conexão estabelecida. Tipo do objeto repo: {type(repo)}")
        
        # Detecção do tipo de repositório para logging
        repo_type = "GitLab" if _is_gitlab_project(repo) else "GitHub"
        print(f"Tipo de repositório detectado: {repo_type}")

        # ETAPA 2: Configuração da estratégia de empilhamento
        # A primeira branch é criada a partir da base_branch
        # Cada branch subsequente é criada a partir da anterior
        branch_anterior = base_branch
        lista_de_grupos = dados_agrupados.get("grupos", [])
        
        # Validação básica dos dados de entrada
        if not lista_de_grupos:
            print("Nenhum grupo de mudanças encontrado para processar.")
            print(f"[DEBUG] SAÍDA processar_e_subir_mudancas_agrupadas: []")
            return []

        # ETAPA 3: Processamento sequencial dos grupos
        # Cada grupo vira uma branch + PR empilhado na sequência
        for i, grupo_atual in enumerate(lista_de_grupos):
            print(f"[DEBUG] Processando grupo {i+1}/{len(lista_de_grupos)}")
            # Extração dos dados do grupo atual
            nome_da_branch_atual = grupo_atual.get("branch_sugerida")
            resumo_do_pr = grupo_atual.get("titulo_pr", "Refatoração Automática")
            descricao_do_pr = grupo_atual.get("resumo_do_pr", "")
            conjunto_de_mudancas = grupo_atual.get("conjunto_de_mudancas", [])

            print(f"[DEBUG]   branch_sugerida: {nome_da_branch_atual}")
            print(f"[DEBUG]   titulo_pr: {resumo_do_pr}")
            print(f"[DEBUG]   número de mudanças: {len(conjunto_de_mudancas)}")

            # Validação de dados do grupo
            if not nome_da_branch_atual:
                print("AVISO: Um grupo foi ignorado por não ter uma 'branch_sugerida'.")
                continue
            
            if not conjunto_de_mudancas:
                print(f"AVISO: O grupo para a branch '{nome_da_branch_atual}' não contém nenhuma mudança e será ignorado.")
                continue

            # ETAPA 3.1: Processamento da branch atual
            # Chama a função especializada para processar uma branch individual
            print(f"[DEBUG] Chamando _processar_uma_branch para {nome_da_branch_atual}")
            resultado_da_branch = _processar_uma_branch(
                repo=repo,
                nome_branch=nome_da_branch_atual,
                branch_de_origem=branch_anterior,  # Empilhamento: usa branch anterior como base
                branch_alvo_do_pr=branch_anterior,  # PR aponta para branch anterior
                mensagem_pr=resumo_do_pr,
                descricao_pr=descricao_pr,
                conjunto_de_mudancas=conjunto_de_mudancas
            )
            print(f"[DEBUG] Resultado da branch {nome_da_branch_atual}: {resultado_da_branch}")
            
            resultados_finais.append(resultado_da_branch)

            # ETAPA 3.2: Atualização da cadeia de empilhamento
            # Se a branch foi processada com sucesso e tem PR, ela vira a nova base
            # Isso mantém a sequência de empilhamento para o próximo grupo
            if resultado_da_branch["success"] and resultado_da_branch.get("pr_url"):
                branch_anterior = nome_da_branch_atual
                print(f"Branch '{nome_da_branch_atual}' será usada como base para o próximo grupo.")
            
            print("-" * 60)  # Separador visual entre grupos
        
        print(f"[DEBUG] SAÍDA processar_e_subir_mudancas_agrupadas: {len(resultados_finais)} resultados")
        for i, resultado in enumerate(resultados_finais):
            print(f"[DEBUG]   Resultado {i+1}: success={resultado.get('success')}, pr_url={resultado.get('pr_url')}, message={resultado.get('message')}")
        
        return resultados_finais

    except Exception as e:
        # Tratamento de erros críticos no orquestrador
        print(f"ERRO FATAL NO ORQUESTRADOR DE COMMITS: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        
        # Retorna resultado de falha estruturado
        error_result = [{"success": False, "message": f"Erro fatal no orquestrador: {e}"}]
        print(f"[DEBUG] SAÍDA processar_e_subir_mudancas_agrupadas (ERRO): {error_result}")
        return error_result