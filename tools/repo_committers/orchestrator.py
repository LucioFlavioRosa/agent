from tools.repo_committers.azure_committer import processar_branch_azure

def executar_azure_commit(repo, nome_branch, branch_de_origem, branch_alvo_do_pr, mensagem_pr, descricao_pr, conjunto_de_mudancas, modo_adicao_incremental=False):
    mudancas_filtradas = []
    for mudanca in conjunto_de_mudancas:
        caminho = mudanca.get('caminho')
        if caminho is None or caminho == '':
            print(f"[ERROR][ORCHESTRATOR] Mudança inválida detectada e removida antes do commit: {mudanca}")
            continue
        mudancas_filtradas.append(mudanca)
    if not mudancas_filtradas:
        return {
            "success": False,
            "error": "Nenhuma mudança válida para commitar. Todas as mudanças estavam sem caminho válido.",
            "branch_name": nome_branch
        }
    return processar_branch_azure(
        repo,
        nome_branch,
        branch_de_origem,
        branch_alvo_do_pr,
        mensagem_pr,
        descricao_pr,
        mudancas_filtradas,
        modo_adicao_incremental
    )
