# Arquivo: tools/github_reader.py (VERSÃO FINAL E CORRIGIDA)

import time
from github import GithubException
from tools import github_connector
import pathspec # Mantemos a importação para o .gitignore

# Mapeamento de extensões, pode ajustar conforme necessário
MAPEAMENTO_TIPO_EXTENSOES = {
    "design": [".tf", ".tfvars", ".py"],
    "relatorio_teste_unitario": [".py"],
    # Adicione outros tipos de análise que você precisar
}

def _ler_arquivos_recursivamente(repo, extensoes, nome_branch: str, spec: pathspec.PathSpec, path: str = "", arquivos_do_repo: dict = None):
    """
    Função recursiva que lê arquivos, ignorando os caminhos definidos no .gitignore.
    """
    if arquivos_do_repo is None:
        arquivos_do_repo = {}
    
    # A chamada abaixo pode gerar um erro 404, que será capturado pela lógica de retentativa no 'main'
    conteudos = repo.get_contents(path, ref=nome_branch)

    for conteudo in conteudos:
        # Verifica se o caminho do arquivo ou diretório é ignorado pelo .gitignore
        if spec.match_file(conteudo.path):
            continue # Pula para o próximo item

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
    Função principal que lê os arquivos de um repositório, respeitando o .gitignore
    e com lógica de retentativa para encontrar a branch.
    """
    repositorio = github_connector.connection(repositorio=nome_repo)
    branch_a_ler = nome_branch if nome_branch else repositorio.default_branch
    
    print(f"--- Iniciando Leitura do Repositório: {nome_repo} (Branch: '{branch_a_ler}') ---")

    # Lógica para buscar e processar o .gitignore
    gitignore_conteudo = ""
    try:
        gitignore_file = repositorio.get_contents(".gitignore", ref=branch_a_ler)
        gitignore_conteudo = gitignore_file.decoded_content.decode('utf-8')
        print("Arquivo .gitignore encontrado e carregado.")
    except GithubException:
        print("AVISO: Nenhum arquivo .gitignore encontrado. Lendo todos os arquivos.")

    # [CORREÇÃO] Usando o "sabor" 'gitignore' que não depende do sistema.
    spec = pathspec.PathSpec.from_lines('gitignore', gitignore_conteudo.splitlines())

    extensoes_alvo = MAPEAMENTO_TIPO_EXTENSOES.get(tipo_de_analise.lower())
    
    # Lógica de retentativa que você forneceu (excelente!)
    max_tentativas = 4
    delay_entre_tentativas = 5
    arquivos_encontrados = None

    for tentativa in range(max_tentativas):
        try:
            print(f"Tentativa {tentativa + 1}/{max_tentativas} para ler a branch '{branch_a_ler}'...")
            arquivos_encontrados = _ler_arquivos_recursivamente(
                repositorio,
                extensoes=extensoes_alvo,
                nome_branch=branch_a_ler,
                spec=spec # Passa o spec para a função recursiva
            )
            print("Leitura da branch bem-sucedida!")
            break 
        except GithubException as e:
            if e.status == 404:
                if tentativa < max_tentativas - 1:
                    print(f"Branch '{branch_a_ler}' não encontrada (erro 404). Aguardando {delay_entre_tentativas}s...")
                    time.sleep(delay_entre_tentativas)
                else:
                    print("Número máximo de tentativas atingido. A branch realmente não foi encontrada.")
                    raise FileNotFoundError(f"A branch '{branch_a_ler}' não foi encontrada no repositório '{nome_repo}' após {max_tentativas} tentativas.") from e
            else:
                print(f"Ocorreu um erro inesperado no GitHub: {e}")
                raise e
    
    if arquivos_encontrados is None:
        # Isso pode acontecer se o loop terminar sem sucesso mas sem lançar erro (improvável, mas seguro)
        raise FileNotFoundError(f"Não foi possível ler nenhum arquivo da branch '{branch_a_ler}'.")

    if not arquivos_encontrados:
        # A leitura foi bem-sucedida, mas nenhum arquivo com as extensões foi encontrado
        raise FileNotFoundError(f"Nenhum arquivo com as extensões para '{tipo_de_analise}' (e não ignorado) foi encontrado na branch '{branch_a_ler}'.")
        
    print(f"\nLeitura concluída. Total de {len(arquivos_encontrados)} arquivos relevantes encontrados.")
    return arquivos_encontrados
