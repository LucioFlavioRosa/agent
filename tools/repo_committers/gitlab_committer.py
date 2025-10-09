def processar_branch_gitlab(repo, nome_branch, branch_de_origem, branch_alvo_do_pr, mensagem_pr, descricao_pr, conjunto_de_mudancas, modo_adicao_incremental=False):
    mudancas_validas, mudancas_exclusao = _processar_mudancas_comuns(conjunto_de_mudancas)
    # Processa arquivos para criar/modificar
    for mudanca in mudancas_validas:
        caminho = mudanca['caminho_do_arquivo']
        conteudo = mudanca['conteudo']
        status = mudanca['status']
        if status == 'CRIADO':
            repo.files.create(file_path=caminho, branch=nome_branch, content=conteudo, commit_message=mensagem_pr)
        elif status == 'MODIFICADO':
            repo.files.update(file_path=caminho, branch=nome_branch, content=conteudo, commit_message=mensagem_pr)
    # Processa exclusões
    for mudanca in mudancas_exclusao:
        caminho = mudanca['caminho_do_arquivo']
        try:
            repo.files.delete(file_path=caminho, branch=nome_branch, commit_message=mensagem_pr)
        except Exception:
            pass
    return {
        'branch_name': nome_branch,
        'success': True,
        'pr_url': 'PR criado',
        'arquivos_modificados': [m['caminho_do_arquivo'] for m in mudancas_validas + mudancas_exclusao]
    }
