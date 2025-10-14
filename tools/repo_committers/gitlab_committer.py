from tools.repo_committers.base_committer import BaseCommitter

def processar_branch_gitlab(repo, nome_branch, branch_de_origem, branch_alvo_do_pr, mensagem_pr, descricao_pr, conjunto_de_mudancas, modo_adicao_incremental=False):
    resultado_branch = BaseCommitter._inicializar_resultado_branch(nome_branch)
    try:
        BaseCommitter._validate_no_duplicate_paths(conjunto_de_mudancas)
    except ValueError as ve:
        BaseCommitter._finalizar_resultado_erro(resultado_branch, str(ve))
        return resultado_branch
    mudancas_validas = BaseCommitter._processar_mudancas_comuns(conjunto_de_mudancas, resultado_branch)
    if not mudancas_validas:
        raise ValueError(f"Tentativa de commit com conjunto de mudanças vazio. Verifique a saída do agente e a formatação dos dados. conjunto_de_mudancas={conjunto_de_mudancas}")
    # ... restante da implementação original ...
    return resultado_branch
