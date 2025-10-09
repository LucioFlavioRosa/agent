def processar_branch_gitlab(repo, nome_branch, branch_de_origem, branch_alvo_do_pr, mensagem_pr, descricao_pr, conjunto_de_mudancas, modo_adicao_incremental=False):
    mudancas_validas, mudancas_exclusao = _processar_mudancas_comuns(conjunto_de_mudancas)
    arquivos_modificados = []
    for mudanca in mudancas_validas:
        caminho = mudanca['caminho_do_arquivo']
        conteudo = mudanca['conteudo']
        if mudanca.get('status') == 'CRIADO':
            repo.files.create(file_path=caminho, branch=nome_branch, content=conteudo, commit_message=mensagem_pr)
        else:
            repo.files.update(file_path=caminho, branch=nome_branch, content=conteudo, commit_message=mensagem_pr)
        arquivos_modificados.append(caminho)
    for mudanca in mudancas_exclusao:
        caminho = mudanca['caminho_do_arquivo']
        try:
            repo.files.delete(file_path=caminho, commit_message=mensagem_pr, branch=nome_branch)
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
