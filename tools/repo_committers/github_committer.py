def processar_branch_github(repo, nome_branch, branch_de_origem, branch_alvo_do_pr, mensagem_pr, descricao_pr, conjunto_de_mudancas, modo_adicao_incremental=False):
    mudancas_validas, mudancas_exclusao = _processar_mudancas_comuns(conjunto_de_mudancas)
    arquivos_modificados = []
    for mudanca in mudancas_validas:
        caminho = mudanca['caminho_do_arquivo']
        conteudo = mudanca['conteudo']
        if mudanca.get('status') == 'CRIADO':
            repo.create_file(caminho, mensagem_pr, conteudo, branch=nome_branch)
        else:
            repo.update_file(caminho, mensagem_pr, conteudo, repo.get_contents(caminho, ref=nome_branch).sha, branch=nome_branch)
        arquivos_modificados.append(caminho)
    for mudanca in mudancas_exclusao:
        caminho = mudanca['caminho_do_arquivo']
        try:
            sha = repo.get_contents(caminho, ref=nome_branch).sha
            repo.delete_file(caminho, mensagem_pr, sha, branch=nome_branch)
            arquivos_modificados.append(caminho)
        except Exception:
            pass
    pr_url = None
    return {
        'branch_name': nome_branch,
        'success': True,
        'pr_url': pr_url,
        'arquivos_modificados': arquivos_modificados
    }
