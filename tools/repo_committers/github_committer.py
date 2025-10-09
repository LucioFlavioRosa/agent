def processar_branch_github(repo, nome_branch, branch_de_origem, branch_alvo_do_pr, mensagem_pr, descricao_pr, conjunto_de_mudancas, modo_adicao_incremental=False):
    mudancas_validas, mudancas_exclusao = _processar_mudancas_comuns(conjunto_de_mudancas)
    # Processa arquivos para criar/modificar
    for mudanca in mudancas_validas:
        caminho = mudanca['caminho_do_arquivo']
        conteudo = mudanca['conteudo']
        status = mudanca['status']
        if status == 'CRIADO':
            repo.create_file(caminho, mensagem_pr, conteudo, branch=nome_branch)
        elif status == 'MODIFICADO':
            arquivo = repo.get_contents(caminho, ref=nome_branch)
            repo.update_file(caminho, mensagem_pr, conteudo, arquivo.sha, branch=nome_branch)
    # Processa exclusões
    for mudanca in mudancas_exclusao:
        caminho = mudanca['caminho_do_arquivo']
        try:
            arquivo = repo.get_contents(caminho, ref=nome_branch)
            repo.delete_file(caminho, mensagem_pr, arquivo.sha, branch=nome_branch)
        except Exception:
            pass
    return {
        'branch_name': nome_branch,
        'success': True,
        'pr_url': 'PR criado',
        'arquivos_modificados': [m['caminho_do_arquivo'] for m in mudancas_validas + mudancas_exclusao]
    }
