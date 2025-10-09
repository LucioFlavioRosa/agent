def processar_branch_azure(repo, nome_branch, branch_de_origem, branch_alvo_do_pr, mensagem_pr, descricao_pr, conjunto_de_mudancas, modo_adicao_incremental=False):
    mudancas_validas, mudancas_exclusao = _processar_mudancas_comuns(conjunto_de_mudancas)
    changes_list = []
    arquivos_modificados = []
    for mudanca in mudancas_validas:
        caminho = mudanca['caminho_do_arquivo']
        conteudo = mudanca['conteudo']
        change_type = 'add' if mudanca.get('status') == 'CRIADO' else 'edit'
        changes_list.append({
            'changeType': change_type,
            'item': {'path': caminho},
            'newContent': {'content': conteudo, 'contentType': 'rawtext'}
        })
        arquivos_modificados.append(caminho)
    for mudanca in mudancas_exclusao:
        caminho = mudanca['caminho_do_arquivo']
        changes_list.append({
            'changeType': 'delete',
            'item': {'path': caminho}
        })
        arquivos_modificados.append(caminho)
    pr_url = None
    return {
        'branch_name': nome_branch,
        'success': True,
        'pr_url': pr_url,
        'arquivos_modificados': arquivos_modificados
    }
