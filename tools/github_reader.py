# Arquivo: tools/github_reader.py (VERSÃO CORRIGIDA E FINAL)

import time
from github import GithubException
from tools import github_connector # Importa o conector inteiro

MAPEAMENTO_TIPO_EXTENSOES = {
    "design": [".tf", ".tfvars", ".py"],
    "relatorio_teste_unitario": [".py"],
    # Adicione outras extensões conforme necessário
}

def _ler_arquivos_recursivamente(repo, extensoes, nome_branch: str, path: str = "", arquivos_do_repo: dict = None):
    if arquivos_do_repo is None:
        arquivos_do_repo = {}

    conteudos = repo.get_contents(path, ref=nome_branch)

    for conteudo in conteudos:
        if conteudo.type == "dir":
            _ler_arquivos_recursivamente(repo, extensoes, nome_branch, conteudo.path, arquivos_do_repo)
        else:
            ler_o_arquivo = False
            if extensoes is None or any(conteudo.path.endswith(ext) for ext in extensoes):
                ler_o_arquivo = True
            
            if ler_o_arquivo:
                try:
                    codigo = conteudo.decoded_content.decode('utf-8')
                    arquivos_do_repo[conteudo.path] = codigo
                except Exception as e:
                    print(f"AVISO: ERRO na decodificação de '{conteudo.path}'. Pulando. Erro: {e}")

    return arquivos_do_repo

def main(nome_repo: str, tipo_de_analise: str, nome_branch: str = None):
    # Chama a nova função que retorna apenas o objeto do repositório
    repositorio = github_connector.get_authenticated_repo(repositorio=nome_repo)

    branch_a_ler = nome_branch if nome_branch else repositorio.default_branch
    print(f"Lendo a branch: '{branch_a_ler}'")

    extensoes_alvo = MAPEAMENTO_TIPO_EXTENSOES.get(tipo_de_analise.lower())
    
    arquivos_encontrados = _ler_arquivos_recursivamente(
        repositorio, # Agora 'repositorio' é o objeto correto, não uma tupla
        extensoes=extensoes_alvo,
        nome_branch=branch_a_ler
    )
    
    if not arquivos_encontrados:
        raise FileNotFoundError(f"Nenhum arquivo com as extensões para '{tipo_de_analise}' foi encontrado na branch '{branch_a_ler}'.")
        
    print(f"Leitura concluída. Total de {len(arquivos_encontrados)} arquivos encontrados.")
    return arquivos_encontrados
