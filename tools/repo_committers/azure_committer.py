def processar_branch_azure(repo, nome_branch, branch_de_origem, branch_alvo_do_pr, mensagem_pr, descricao_pr, conjunto_de_mudancas, modo_adicao_incremental=False):
    mudancas_validas, mudancas_exclusao = _processar_mudancas_comuns(conjunto_de_mudancas)
    changes_list = []
    for mudanca in mudancas_validas:
        caminho = mudanca['caminho_do_arquivo']
        conteudo = mudanca['conteudo']
        changes_list.append({
            'changeType': 'edit',
            'item': {'path': caminho},
            'newContent': {'content': conteudo, 'contentType': 'rawtext'}
        })
    for mudanca in mudancas_exclusao:
        caminho = mudanca['caminho_do_arquivo']
        changes_list.append({
            'changeType': 'delete',
            'item': {'path': caminho}
        })
    repo.push_changes(branch=nome_branch, changes=changes_list, commit_message=mensagem_pr)
    arquivos_modificados = [m['caminho_do_arquivo'] for m in mudancas_validas + mudancas_exclusao]
    pr_url = 'PR criado (azure)'
    return {
        'branch_name': nome_branch,
        'success': True,
        'pr_url': pr_url,
        'message': mensagem_pr,
        'arquivos_modificados': arquivos_modificados
    }
