# Arquivo: tools/github_reader.py (VERSÃO ROBUSTA COM .gitignore)

from github import GithubException
from tools import github_connector
import pathspec # [NOVO] Importa a biblioteca para parsear o .gitignore

MAPEAMENTO_TIPO_EXTENSOES = {
    "design": [".tf", ".tfvars", ".py"],
    "relatorio_teste_unitario": [".py"],
}

def _ler_arquivos_recursivamente(repo, extensoes, nome_branch: str, spec: pathspec.PathSpec, path: str = "", arquivos_do_repo: dict = None):
    """
    Função recursiva que lê arquivos, agora ignorando os caminhos definidos no .gitignore.
    """
    if arquivos_do_repo is None:
        arquivos_do_repo = {}
    
    conteudos = repo.get_contents(path, ref=nome_branch)
    for conteudo in conteudos:
        # [NOVO] Verifica se o caminho do arquivo ou diretório é ignorado pelo .gitignore
        if spec.match_file(conteudo.path):
            print(f"  [IGNORADO] Caminho '{conteudo.path}' corresponde a uma regra do .gitignore.")
            continue

        if conteudo.type == "dir":
            _ler_arquivos_recursivamente(repo, extensoes, nome_branch, spec, conteudo.path, arquivos_do_repo)
        else:
            if extensoes is None or any(conteudo.path.endswith(ext) for ext in extensoes):
                try:
                    codigo = conteudo.decoded_content.decode('utf-8')
                    arquivos_do_repo[conteudo.path] = codigo
                except Exception as e:
                    print(f"AVISO: ERRO na decodificação de '{conteudo.path}'. Pulando. Erro: {e}")
    return arquivos_do_repo

def main(nome_repo: str, tipo_de_analise: str, nome_branch: str = None):
    """
    Função principal que lê os arquivos de um repositório, respeitando o .gitignore.
    """
    repositorio = github_connector.connection(repositorio=nome_repo)
    branch_a_ler = nome_branch if nome_branch else repositorio.default_branch
    
    print(f"--- Iniciando Leitura do Repositório: {nome_repo} ---")
    print(f"Lendo a branch: '{branch_a_ler}'")

    # [NOVO] Lógica para buscar e processar o .gitignore
    gitignore_conteudo = ""
    try:
        gitignore_file = repositorio.get_contents(".gitignore", ref=branch_a_ler)
        gitignore_conteudo = gitignore_file.decoded_content.decode('utf-8')
        print("Arquivo .gitignore encontrado e carregado.")
    except GithubException as e:
        if e.status == 404:
            print("AVISO: Nenhum arquivo .gitignore encontrado no repositório. Lendo todos os arquivos.")
        else:
            raise

    # Cria um 'spec' a partir das regras do gitignore
    spec = pathspec.PathSpec.from_lines('git', gitignore_conteudo.splitlines())

    extensoes_alvo = MAPEAMENTO_TIPO_EXTENSOES.get(tipo_de_analise.lower())
    
    arquivos_encontrados = _ler_arquivos_recursivamente(
        repositorio,
        extensoes=extensoes_alvo,
        nome_branch=branch_a_ler,
        spec=spec # Passa o spec para a função recursiva
    )
    
    if not arquivos_encontrados:
        raise FileNotFoundError(f"Nenhum arquivo com as extensões para '{tipo_de_analise}' (e não ignorado) foi encontrado na branch '{branch_a_ler}'.")
        
    print(f"Leitura concluída. Total de {len(arquivos_encontrados)} arquivos relevantes encontrados.")
    return arquivos_encontrados
