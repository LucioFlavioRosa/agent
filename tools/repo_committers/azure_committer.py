def processar_branch_azure(repo, nome_branch, branch_de_origem, branch_alvo_do_pr, mensagem_pr, descricao_pr, conjunto_de_mudancas, modo_adicao_incremental=False):
    mudancas_validas, mudancas_exclusao = _processar_mudancas_comuns(conjunto_de_mudancas)
    changes_list = []
    for mudanca in mudancas_validas:
        caminho = mudanca['caminho_do_arquivo']
        conteudo = mudanca['conteudo']
        status = mudanca['status']
        if status == 'CRIADO':
            changes_list.append({
                'changeType': 'add',
                'item': {'path': caminho},
                'newContent': {'content': conteudo, 'contentType': 'rawtext'}
            })
        elif status == 'MODIFICADO':
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
    repo.push_changes(changes_list, branch=nome_branch, commit_message=mensagem_pr)
    return {
        'branch_name': nome_branch,
        'success': True,
        'pr_url': 'PR criado',
        'arquivos_modificados': [m['caminho_do_arquivo'] for m in mudancas_validas + mudancas_exclusao]
    }
