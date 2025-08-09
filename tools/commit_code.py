import json
from github import GithubException
from tools import github_connector

def aplicar_mudancas_no_github(
    nome_repo: str,      
    nome_branch: str,      
    mensagem_pr: str,
    dados_mudancas: dict,  
    base_branch: str = "main"
):
    """
    Aplica um conjunto de mudanças de arquivos a um repositório GitHub,
    criando um commit por arquivo com assunto e corpo (justificativa),
    e depois abrindo um Pull Request.
    """
    try:
        print("Conectando ao GitHub...")
        repo = github_connector.connection(repositorio=nome_repo)
        print(f"Conectado com sucesso ao repositório: {repo.full_name}")

        print(f"Criando ou reutilizando a branch '{nome_branch}' a partir de '{base_branch}'...")
        try:
            ref_base = repo.get_git_ref(f"heads/{base_branch}")
            repo.create_git_ref(ref=f"refs/heads/{nome_branch}", sha=ref_base.object.sha)
            print(f"Branch '{nome_branch}' criada com sucesso.")
        except GithubException as e:
            if e.status == 422 and "Reference already exists" in str(e.data): 
                print(f"AVISO: A branch '{nome_branch}' já existe. Os novos commits serão adicionados a ela.")
            else:
                raise 

        conjunto_de_mudancas = dados_mudancas.get("conjunto_de_mudancas", [])
        if not conjunto_de_mudancas:
            print("Nenhuma mudança para aplicar.")
            return

        print("\nIniciando a aplicação dos arquivos no repositório (um commit por arquivo)...")
        for mudanca in conjunto_de_mudancas:
            caminho = mudanca.get("caminho_do_arquivo")
            conteudo = mudanca.get("conteudo")
            # --- NOVO: Extrai a justificativa para usar no corpo do commit ---
            justificativa = mudanca.get("justificativa")

            if not caminho or conteudo is None:
                print(f"AVISO: Pulando mudança inválida (sem caminho ou conteúdo): {mudanca}")
                continue
            
            sha_arquivo_existente = None
            try:
                arquivo_existente = repo.get_contents(caminho, ref=nome_branch)
                sha_arquivo_existente = arquivo_existente.sha
            except GithubException as e:
                if e.status != 404:
                    print(f"ERRO ao verificar o arquivo '{caminho}': {e}")
                    continue

            try:
                # Define o assunto (subject) do commit
                assunto_commit = f"Refatora: {caminho}" if sha_arquivo_existente else f"Adiciona: {caminho}"
                
                # --- NOVO: Constrói a mensagem de commit completa ---
                # O padrão Git separa o assunto do corpo com UMA linha em branco (duas quebras de linha \n\n).
                if justificativa:
                    commit_message_completo = f"{assunto_commit}\n\n{justificativa}"
                else:
                    commit_message_completo = assunto_commit

                if sha_arquivo_existente:
                    repo.update_file(
                        path=caminho,
                        message=commit_message_completo, # Usa a mensagem completa
                        content=conteudo,
                        sha=sha_arquivo_existente,
                        branch=nome_branch
                    )
                    print(f"  [MODIFICADO] {caminho} (commit criado com justificativa)")
                else:
                    repo.create_file(
                        path=caminho,
                        message=commit_message_completo, # Usa a mensagem completa
                        content=conteudo,
                        branch=nome_branch
                    )
                    print(f"  [CRIADO]     {caminho} (commit criado com justificativa)")

            except GithubException as e:
                print(f"ERRO ao commitar o arquivo '{caminho}': {e}")

        print("\nAplicação de arquivos e commits concluída.")

        # A criação do Pull Request continua a mesma
        try:
            print(f"\nCriando Pull Request de '{nome_branch}' para '{base_branch}'...")
            pr = repo.create_pull(
                title=mensagem_pr,
                body=dados_mudancas.get("resumo_geral", "Alterações aplicadas automaticamente por agente de IA."),
                head=nome_branch,
                base=base_branch
            )
            print(f"Pull Request criado com sucesso! Acesse em: {pr.html_url}")
        except GithubException as e:
            if e.status == 422 and "A pull request for these commits already exists" in str(e.data.get('message', '')):
                print(f"AVISO: Um Pull Request para a branch '{nome_branch}' já existe.")
            else:
                print(f"AVISO: Não foi possível criar o Pull Request. Erro: {e}")

    except Exception as e:
        print(f"ERRO FATAL NO PROCESSO: {e}")