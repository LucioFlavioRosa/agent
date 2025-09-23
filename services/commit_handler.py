from typing import Dict, Any
from tools.conectores.conexao_geral import ConexaoGeral
from tools.repo_committers.orchestrator import processar_branch_por_provedor
from tools.repository_provider_factory import get_repository_provider_explicit

class CommitHandler:
    def __init__(self, repository_provider_factory=None, conexao_geral_factory=None):
        self.repository_provider_factory = repository_provider_factory or get_repository_provider_explicit
        self.conexao_geral_factory = conexao_geral_factory or ConexaoGeral.create_with_defaults
    
    def execute_commits(self, job_id: str, job_info: Dict[str, Any], dados_finais_formatados: Dict[str, Any], 
                      repository_type: str, repo_name: str) -> None:
        branch_base_para_pr = job_info['data'].get('branch_name', 'main')

        print(f"[{job_id}] Iniciando commit com repositório: '{repo_name}' (tipo: {repository_type})")

        repository_provider = self.repository_provider_factory(repository_type)
        conexao_geral = self.conexao_geral_factory()
        repo = conexao_geral.connection(
            repositorio=repo_name,
            repository_type=repository_type,
            repository_provider=repository_provider
        )

        commit_results = []
        for grupo in dados_finais_formatados["grupos"]:
            print(f"[{job_id}] Processando grupo: {grupo.get('titulo_pr', 'Sem título')}")
            
            resultado_branch = processar_branch_por_provedor(
                repo=repo,
                nome_branch=grupo["branch_sugerida"],
                branch_de_origem=branch_base_para_pr,
                branch_alvo_do_pr=branch_base_para_pr,
                mensagem_pr=grupo["titulo_pr"],
                descricao_pr=grupo["resumo_do_pr"],
                conjunto_de_mudancas=grupo["conjunto_de_mudancas"],
                repository_type=repository_type
            )
            
            print(f"[{job_id}] DIAGNÓSTICO DETALHADO - Resultado bruto do processar_branch_por_provedor:")
            print(f"[{job_id}] DIAGNÓSTICO - success: {resultado_branch.get('success')}")
            print(f"[{job_id}] DIAGNÓSTICO - pr_url: '{resultado_branch.get('pr_url')}'")
            print(f"[{job_id}] DIAGNÓSTICO - branch_name: '{resultado_branch.get('branch_name')}'")
            print(f"[{job_id}] DIAGNÓSTICO - message: '{resultado_branch.get('message')}'")
            print(f"[{job_id}] DIAGNÓSTICO - arquivos_modificados: {resultado_branch.get('arquivos_modificados', [])}")
            print(f"[{job_id}] DIAGNÓSTICO - Resultado completo: {resultado_branch}")
            
            if not resultado_branch.get('pr_url') and resultado_branch.get('success'):
                print(f"[{job_id}] AVISO CRÍTICO - PR marcado como sucesso mas pr_url está vazio/None")
                resultado_branch['pr_url'] = f"PR criado com sucesso para branch: {resultado_branch.get('branch_name', 'branch-desconhecida')}"
                print(f"[{job_id}] CORREÇÃO - pr_url definido como fallback: '{resultado_branch['pr_url']}'")
            
            if resultado_branch.get('success'):
                if resultado_branch.get('pr_url'):
                    print(f"[{job_id}] PR criado com sucesso: {resultado_branch.get('pr_url')}")
                else:
                    print(f"[{job_id}] ERRO CRÍTICO - PR criado com sucesso mas pr_url continua vazio após correção")
            else:
                print(f"[{job_id}] ERRO - Falha ao criar PR: {resultado_branch.get('message', 'Erro desconhecido')}")
            
            commit_results.append(resultado_branch)

        print(f"[{job_id}] Commit concluído. Resultados: {len(commit_results)} branches processadas")
        print(f"[{job_id}] DIAGNÓSTICO FINAL - commit_results antes de salvar no job_info:")
        for i, result in enumerate(commit_results):
            print(f"[{job_id}] DIAGNÓSTICO - PR {i+1}: success={result.get('success')}, pr_url='{result.get('pr_url')}', branch_name='{result.get('branch_name')}', arquivos_modificados={len(result.get('arquivos_modificados', []))}")
        
        job_info['data']['commit_details'] = commit_results
        
        print(f"[{job_id}] DIAGNÓSTICO - commit_details salvo no job_info com {len(job_info['data']['commit_details'])} itens")
        print(f"[{job_id}] DIAGNÓSTICO - Verificação pós-salvamento do commit_details:")
        for i, result in enumerate(job_info['data']['commit_details']):
            print(f"[{job_id}] DIAGNÓSTICO - Item {i+1} salvo: success={result.get('success')}, pr_url='{result.get('pr_url')}', branch_name='{result.get('branch_name')}'")