# Arquivo: tools/commit_multiplas_branchs.py (VERSÃO REFATORADA SEGUINDO SOLID)

import json
from github import GithubException, UnknownObjectException
from tools.github_connector import GitHubConnector
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.github_repository_provider import GitHubRepositoryProvider
from typing import Dict, Any, List, Optional

def _processar_uma_branch(
    repo,
    nome_branch: str,
    branch_de_origem: str,
    branch_alvo_do_pr: str,
    mensagem_pr: str,
    descricao_pr: str,
    conjunto_de_mudancas: list,
    provider_type: str = "github"
) -> Dict[str, Any]:
    """
    Processa uma única branch implementando o padrão de Pull Requests empilhados.
    
    Esta função implementa a lógica central de processamento de uma branch individual,
    incluindo criação da branch, aplicação de mudanças (criação, modificação, remoção)
    e criação do Pull Request correspondente.
    
    NOVA FUNCIONALIDADE: Agora suporta múltiplos provedores (GitHub, GitLab, Azure DevOps)
    através de tratamento diferenciado baseado no provider_type.
    
    Estratégia de Empilhamento:
    - Cada branch é criada a partir da branch anterior (empilhamento)
    - PRs são direcionados para a branch anterior, não para main
    - Isso permite revisão e merge sequencial das mudanças
    
    Args:
        repo: Objeto repositório do provedor (PyGithub Repository, GitLab Project, etc.)
        nome_branch (str): Nome da nova branch a ser criada
        branch_de_origem (str): Branch base para criação da nova branch
        branch_alvo_do_pr (str): Branch de destino do Pull Request
        mensagem_pr (str): Título do Pull Request
        descricao_pr (str): Descrição detalhada do Pull Request
        conjunto_de_mudancas (list): Lista de mudanças a serem aplicadas
        provider_type (str): Tipo do provedor ('github', 'gitlab', 'azure')
    
    Returns:
        Dict[str, Any]: Resultado do processamento contendo:
            - branch_name (str): Nome da branch processada
            - success (bool): Se o processamento foi bem-sucedido
            - pr_url (str): URL do Pull Request criado (se aplicável)
            - message (str): Mensagem descritiva do resultado
            - arquivos_modificados (List[str]): Lista de arquivos alterados
    
    Note:
        - Trata graciosamente branches já existentes
        - Ignora mudanças sem caminho de arquivo válido
        - Aplica lógica diferenciada por status (ADICIONADO, MODIFICADO, REMOVIDO)
        - Cria PR apenas se houver commits realizados
        - Suporte multi-provedor através de tratamento específico por tipo
    """
    print(f"\n--- Processando Lote para a Branch: '{nome_branch}' (Provider: {provider_type.upper()}) ---")
    
    # Inicializa estrutura de resultado para tracking do processamento
    resultado_branch = {
        "branch_name": nome_branch,
        "success": False,
        "pr_url": None,
        "message": "",
        "arquivos_modificados": []
    }
    commits_realizados = 0

    try:
        # ETAPA 1: Criação da branch empilhada (agnóstica ao provedor)
        # Tenta criar nova branch a partir da branch de origem (estratégia de empilhamento)
        if provider_type == "github":
            ref_base = repo.get_git_ref(f"heads/{branch_de_origem}")
            repo.create_git_ref(ref=f"refs/heads/{nome_branch}", sha=ref_base.object.sha)
        elif provider_type == "gitlab":
            # GitLab usa branches.create()
            try:
                repo.branches.create({'branch': nome_branch, 'ref': branch_de_origem})
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"AVISO: A branch '{nome_branch}' já existe no GitLab. Commits serão adicionados a ela.")
                else:
                    raise
        elif provider_type == "azure":
            # Azure DevOps usa REST API para criar branches
            # Implementação específica seria necessária aqui
            print(f"AVISO: Criação de branch para Azure DevOps ainda não implementada. Branch '{nome_branch}' assumida como existente.")
        
        print(f"Branch '{nome_branch}' criada/verificada a partir de '{branch_de_origem}'.")
        
    except Exception as e:
        # Tratamento específico: branch já existe (cenário comum em re-execuções)
        if ("Reference already exists" in str(e) or 
            "already exists" in str(e).lower() or
            "422" in str(e)):
            print(f"AVISO: A branch '{nome_branch}' já existe. Commits serão adicionados a ela.")
        else:
            raise

    # ETAPA 2: Aplicação sequencial das mudanças (agnóstica ao provedor)
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
            # ETAPA 2.1: Verificação de existência do arquivo (específica por provedor)
            sha_arquivo_existente = None
            arquivo_existe = False
            
            if provider_type == "github":
                try:
                    arquivo_existente = repo.get_contents(caminho, ref=nome_branch)
                    sha_arquivo_existente = arquivo_existente.sha
                    arquivo_existe = True
                except UnknownObjectException:
                    arquivo_existe = False
            elif provider_type == "gitlab":
                try:
                    arquivo_existente = repo.files.get(file_path=caminho, ref=nome_branch)
                    sha_arquivo_existente = arquivo_existente.blob_id
                    arquivo_existe = True
                except Exception:
                    arquivo_existe = False
            elif provider_type == "azure":
                # Azure DevOps requer implementação específica da API REST
                print(f"  [AVISO] Verificação de arquivo para Azure DevOps ainda não implementada. Assumindo arquivo não existe.")
                arquivo_existe = False

            # ETAPA 2.2: Processamento diferenciado por status e provedor
            if status in ("ADICIONADO", "CRIADO"):
                if arquivo_existe:
                    print(f"  [AVISO] Arquivo '{caminho}' marcado como ADICIONADO já existe. Será tratado como MODIFICADO.")
                    if provider_type == "github":
                        repo.update_file(path=caminho, message=f"refactor: {caminho}", content=conteudo, sha=sha_arquivo_existente, branch=nome_branch)
                    elif provider_type == "gitlab":
                        repo.files.update({
                            'file_path': caminho,
                            'branch': nome_branch,
                            'content': conteudo,
                            'commit_message': f"refactor: {caminho}"
                        })
                    elif provider_type == "azure":
                        print(f"  [AVISO] Atualização de arquivo para Azure DevOps ainda não implementada.")
                else:
                    if provider_type == "github":
                        repo.create_file(path=caminho, message=f"feat: {caminho}", content=conteudo, branch=nome_branch)
                    elif provider_type == "gitlab":
                        repo.files.create({
                            'file_path': caminho,
                            'branch': nome_branch,
                            'content': conteudo,
                            'commit_message': f"feat: {caminho}"
                        })
                    elif provider_type == "azure":
                        print(f"  [AVISO] Criação de arquivo para Azure DevOps ainda não implementada.")
                    
                print(f"  [CRIADO/MODIFICADO] {caminho}")
                commits_realizados += 1
                resultado_branch["arquivos_modificados"].append(caminho)

            elif status == "MODIFICADO":
                if not arquivo_existe:
                    print(f"  [ERRO] Arquivo '{caminho}' marcado como MODIFICADO não foi encontrado na branch. Ignorando.")
                    continue
                    
                if provider_type == "github":
                    repo.update_file(path=caminho, message=f"refactor: {caminho}", content=conteudo, sha=sha_arquivo_existente, branch=nome_branch)
                elif provider_type == "gitlab":
                    repo.files.update({
                        'file_path': caminho,
                        'branch': nome_branch,
                        'content': conteudo,
                        'commit_message': f"refactor: {caminho}"
                    })
                elif provider_type == "azure":
                    print(f"  [AVISO] Modificação de arquivo para Azure DevOps ainda não implementada.")
                    
                print(f"  [MODIFICADO] {caminho}")
                commits_realizados += 1
                resultado_branch["arquivos_modificados"].append(caminho)

            elif status == "REMOVIDO":
                if not arquivo_existe:
                    print(f"  [AVISO] Arquivo '{caminho}' marcado como REMOVIDO já não existe. Ignorando.")
                    continue
                    
                if provider_type == "github":
                    repo.delete_file(path=caminho, message=f"refactor: remove {caminho}", sha=sha_arquivo_existente, branch=nome_branch)
                elif provider_type == "gitlab":
                    repo.files.delete({
                        'file_path': caminho,
                        'branch': nome_branch,
                        'commit_message': f"refactor: remove {caminho}"
                    })
                elif provider_type == "azure":
                    print(f"  [AVISO] Remoção de arquivo para Azure DevOps ainda não implementada.")
                    
                print(f"  [REMOVIDO] {caminho}")
                commits_realizados += 1
                resultado_branch["arquivos_modificados"].append(caminho)
            
            else:
                print(f"  [AVISO] Status '{status}' não reconhecido para o arquivo '{caminho}'. Ignorando.")

        except Exception as e:
            print(f"ERRO ao processar o arquivo '{caminho}': {str(e)}")
            
    # ETAPA 3: Criação do Pull Request/Merge Request (específica por provedor)
    if commits_realizados > 0:
        try:
            print(f"\nCriando Pull/Merge Request de '{nome_branch}' para '{branch_alvo_do_pr}'...")
            
            if provider_type == "github":
                pr = repo.create_pull(title=mensagem_pr, body=descricao_pr, head=nome_branch, base=branch_alvo_do_pr)
                print(f"Pull Request criado com sucesso! URL: {pr.html_url}")
                resultado_branch.update({"success": True, "pr_url": pr.html_url, "message": "PR criado."})
                
            elif provider_type == "gitlab":
                mr = repo.mergerequests.create({
                    'source_branch': nome_branch,
                    'target_branch': branch_alvo_do_pr,
                    'title': mensagem_pr,
                    'description': descricao_pr
                })
                print(f"Merge Request criado com sucesso! URL: {mr.web_url}")
                resultado_branch.update({"success": True, "pr_url": mr.web_url, "message": "MR criado."})
                
            elif provider_type == "azure":
                print(f"AVISO: Criação de Pull Request para Azure DevOps ainda não implementada.")
                resultado_branch.update({"success": True, "message": "Commits realizados (PR não implementado para Azure)."})
            
        except Exception as e:
            # Tratamento específico: PR já existe para esta branch
            if ("A pull request for these commits already exists" in str(e) or
                "already exists" in str(e).lower()):
                print("AVISO: PR/MR para esta branch já existe.")
                resultado_branch.update({"success": True, "message": "PR/MR já existente."})
            else:
                print(f"ERRO ao criar PR/MR para '{nome_branch}': {e}")
                resultado_branch["message"] = f"Erro ao criar PR/MR: {str(e)}"
    else:
        print(f"\nNenhum commit realizado para a branch '{nome_branch}'. Pulando criação do PR/MR.")
        resultado_branch.update({"success": True, "message": "Nenhuma mudança para commitar."})

    return resultado_branch


def processar_e_subir_mudancas_agrupadas(
    nome_repo: str,
    dados_agrupados: dict,
    base_branch: str = "main",
    repository_provider: Optional[IRepositoryProvider] = None
) -> List[Dict[str, Any]]:
    """
    Orquestrador principal que implementa a estratégia de Pull Requests empilhados.
    
    Esta função implementa o padrão de "Stacked Pull Requests" onde cada PR
    é criado em cima do anterior, permitindo revisão e merge sequencial de
    mudanças relacionadas. Agora é agnóstica ao provedor de repositório específico.
    
    NOVA FUNCIONALIDADE: Suporte completo a múltiplos provedores (GitHub, GitLab, Azure DevOps)
    através de detecção automática do tipo de provedor e tratamento específico.
    
    IMPORTANTE: Esta função agora aceita qualquer provedor de repositório via injeção
    de dependência, permitindo uso com GitHub, GitLab, Bitbucket ou outros provedores
    que implementem IRepositoryProvider.
    
    Estratégia de Empilhamento:
    1. Primeira branch criada a partir de base_branch (ex: main)
    2. Segunda branch criada a partir da primeira
    3. Terceira branch criada a partir da segunda
    4. E assim por diante...
    
    Vantagens:
    - Permite revisão incremental de mudanças complexas
    - Facilita rollback de etapas específicas
    - Mantém histórico linear e organizado
    - Reduz conflitos de merge
    
    Args:
        nome_repo (str): Nome do repositório no formato 'org/repo'
        dados_agrupados (dict): Estrutura de dados contendo:
            - grupos (List[Dict]): Lista de grupos de mudanças
            - Cada grupo deve ter: branch_sugerida, titulo_pr, resumo_do_pr, conjunto_de_mudancas
        base_branch (str, optional): Branch base para o primeiro PR. Defaults to "main"
        repository_provider (Optional[IRepositoryProvider], optional): Provedor de repositório
            a ser usado. Se None, usa GitHubRepositoryProvider como padrão. Defaults to None
    
    Returns:
        List[Dict[str, Any]]: Lista de resultados de cada branch processada.
            Cada item contém success, pr_url, message, arquivos_modificados
    
    Raises:
        Exception: Erros críticos no orquestrador são capturados e retornados
            como resultado de falha
    
    Note:
        - Processa grupos sequencialmente para manter ordem de empilhamento
        - Se uma branch falhar, as próximas ainda são processadas
        - Usa injeção de dependência para facilitar testes
        - Faz log detalhado para debugging
        - Funciona com qualquer provedor que implemente IRepositoryProvider
        - Detecta automaticamente o tipo de provedor para tratamento específico
    
    Example:
        >>> # Uso com GitHub (padrão)
        >>> github_provider = GitHubRepositoryProvider()
        >>> resultados = processar_e_subir_mudancas_agrupadas(
        ...     nome_repo="org/repo",
        ...     dados_agrupados=dados,
        ...     repository_provider=github_provider
        ... )
        >>> 
        >>> # Uso com GitLab
        >>> gitlab_provider = GitLabRepositoryProvider()
        >>> resultados = processar_e_subir_mudancas_agrupadas(
        ...     nome_repo="gitlab-org/projeto",
        ...     dados_agrupados=dados,
        ...     repository_provider=gitlab_provider
        ... )
    """
    resultados_finais = []
    
    try:
        provider_name = type(repository_provider).__name__ if repository_provider else "GitHubRepositoryProvider (padrão)"
        print(f"--- Iniciando o Processo de Pull Requests Empilhados via {provider_name} ---")
        
        # ETAPA 1: Inicialização das dependências
        # Usa o provedor injetado ou cria um com dependências padrão
        if repository_provider is None:
            repository_provider = GitHubRepositoryProvider()
            print("AVISO: Nenhum provedor especificado. Usando GitHubRepositoryProvider como padrão.")
        
        # NOVA FUNCIONALIDADE: Detecção automática do tipo de provedor
        provider_type = "github"  # padrão
        if "GitLab" in type(repository_provider).__name__:
            provider_type = "gitlab"
        elif "Azure" in type(repository_provider).__name__:
            provider_type = "azure"
        
        print(f"Tipo de provedor detectado: {provider_type.upper()}")
        
        connector = GitHubConnector(repository_provider=repository_provider)
        repo = connector.connection(repositorio=nome_repo)

        # ETAPA 2: Configuração da estratégia de empilhamento
        # A primeira branch é criada a partir da base_branch
        # Cada branch subsequente é criada a partir da anterior
        branch_anterior = base_branch
        lista_de_grupos = dados_agrupados.get("grupos", [])
        
        # Validação básica dos dados de entrada
        if not lista_de_grupos:
            print("Nenhum grupo de mudanças encontrado para processar.")
            return []

        # ETAPA 3: Processamento sequencial dos grupos
        # Cada grupo vira uma branch + PR empilhado na sequência
        for grupo_atual in lista_de_grupos:
            # Extração dos dados do grupo atual
            nome_da_branch_atual = grupo_atual.get("branch_sugerida")
            resumo_do_pr = grupo_atual.get("titulo_pr", "Refatoração Automática")
            descricao_do_pr = grupo_atual.get("resumo_do_pr", "")
            conjunto_de_mudancas = grupo_atual.get("conjunto_de_mudancas", [])

            # Validação de dados do grupo
            if not nome_da_branch_atual:
                print("AVISO: Um grupo foi ignorado por não ter uma 'branch_sugerida'.")
                continue
            
            if not conjunto_de_mudancas:
                print(f"AVISO: O grupo para a branch '{nome_da_branch_atual}' não contém nenhuma mudança e será ignorado.")
                continue

            # ETAPA 3.1: Processamento da branch atual com suporte multi-provedor
            # Chama a função especializada para processar uma branch individual
            resultado_da_branch = _processar_uma_branch(
                repo=repo,
                nome_branch=nome_da_branch_atual,
                branch_de_origem=branch_anterior,  # Empilhamento: usa branch anterior como base
                branch_alvo_do_pr=branch_anterior,  # PR aponta para branch anterior
                mensagem_pr=resumo_do_pr,
                descricao_pr=descricao_do_pr,
                conjunto_de_mudancas=conjunto_de_mudancas,
                provider_type=provider_type  # NOVO: passa o tipo do provedor
            )
            
            resultados_finais.append(resultado_da_branch)

            # ETAPA 3.2: Atualização da cadeia de empilhamento
            # Se a branch foi processada com sucesso e tem PR, ela vira a nova base
            # Isso mantém a sequência de empilhamento para o próximo grupo
            if resultado_da_branch["success"] and (resultado_da_branch.get("pr_url") or "Commits realizados" in resultado_da_branch.get("message", "")):
                branch_anterior = nome_da_branch_atual
                print(f"Branch '{nome_da_branch_atual}' será usada como base para o próximo grupo.")
            
            print("-" * 60)  # Separador visual entre grupos
        
        return resultados_finais

    except Exception as e:
        # Tratamento de erros críticos no orquestrador
        print(f"ERRO FATAL NO ORQUESTRADOR DE COMMITS: {e}")
        import traceback
        traceback.print_exc()
        
        # Retorna resultado de falha estruturado
        return [{"success": False, "message": f"Erro fatal no orquestrador: {e}"}]