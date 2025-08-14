import re
import time
import yaml 
import os
from github import GithubException
from tools import github_connector

# O mapeamento permanece o mesmo
MAPEAMENTO_TIPO_EXTENSOES = {
    "relatorio_analise_de_design_de_codigo": [".py"],
    "relatorio_refatoracao_codigo": [".py"],
    "relatorio_documentacao_codigo": [".py"],
    "relatorio_avaliacao_terraform": [".tf"],
}

def _carregar_config_workflows():
    """Lê o arquivo YAML e extrai apenas o mapeamento de extensões."""
    try:
        # [NOVO] Constrói um caminho absoluto para o arquivo YAML para garantir que ele seja sempre encontrado.
        # Pega o diretório do arquivo atual (ex: /path/to/project/tools)
        script_dir = os.path.dirname(__file__)
        # Sobe um nível para a raiz do projeto (ex: /path/to/project)
        project_root = os.path.abspath(os.path.join(script_dir, '..'))
        # Monta o caminho completo para o workflows.yaml na raiz
        yaml_path = os.path.join(project_root, 'workflows.yaml')

        # [ALTERADO] Usa o caminho absoluto para abrir o arquivo
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        mapeamento = {
            workflow_name: data.get('extensions', [])
            for workflow_name, data in config.items()
        }
        print(f"Mapeamento de extensões carregado a partir de: {yaml_path}")
        return mapeamento
    except FileNotFoundError:
        print("ERRO CRÍTICO: Arquivo 'workflows.yaml' não encontrado na raiz do projeto.")
        return {}
    except Exception as e:
        print(f"ERRO ao ler ou processar 'workflows.yaml': {e}")
        return {}
        
MAPEAMENTO_TIPO_EXTENSOES = _carregar_config_workflows()

def _ler_arquivos_recursivamente(repo, extensoes, nome_branch: str, path: str = "", arquivos_do_repo: dict = None):
    """
    Função auxiliar que lê recursivamente os arquivos de um repositório em uma branch específica.
    """
    if arquivos_do_repo is None:
        arquivos_do_repo = {}

    conteudos = repo.get_contents(path, ref=nome_branch)

    for conteudo in conteudos:
        if conteudo.type == "dir":
            _ler_arquivos_recursivamente(repo, extensoes, nome_branch, conteudo.path, arquivos_do_repo)
        else:
            ler_o_arquivo = False
            if extensoes is None:
                ler_o_arquivo = True
            else:
                if any(conteudo.path.endswith(ext) for ext in extensoes) or conteudo.name in extensoes:
                    ler_o_arquivo = True
            
            if ler_o_arquivo:
                try:
                    codigo = conteudo.decoded_content.decode('utf-8')
                    arquivos_do_repo[conteudo.path] = codigo
                except Exception as e:
                    print(f"AVISO: ERRO na decodificação de '{conteudo.path}' na branch '{nome_branch}'. Pulando arquivo. Erro: {e}")

    return arquivos_do_repo

# [CORRIGIDO] O nome do parâmetro "tipo_de_analise" foi alterado para "tipo_analise" para ser consistente.
def main(nome_repo: str, tipo_analise: str, nome_branch: str = None):
    """
    Função principal que conecta ao repositório e inicia a leitura dos arquivos
    a partir de uma branch específica, com lógica de retentativa.
    """
    repositorio = github_connector.connection(repositorio=nome_repo)

    if nome_branch is None:
        branch_a_ler = repositorio.default_branch
        print(f"Nenhuma branch especificada. Usando a branch padrão: '{branch_a_ler}'")
    else:
        branch_a_ler = nome_branch
        print(f"Tentando ler a branch especificada: '{branch_a_ler}'")

    # [CORRIGIDO] A variável agora usa o nome de parâmetro correto.
    extensoes_alvo = MAPEAMENTO_TIPO_EXTENSOES.get(tipo_analise.lower())
    if extensoes_alvo is None:
        raise ValueError(f"Tipo de análise '{tipo_analise}' não encontrado ou não possui 'extensions' definidas em workflows.yaml")

    max_tentativas = 4
    delay_entre_tentativas = 5
    arquivos_encontrados = None

    for tentativa in range(max_tentativas):
        try:
            print(f"Tentativa {tentativa + 1} de {max_tentativas}...")
            arquivos_encontrados = _ler_arquivos_recursivamente(
                repositorio,
                extensoes=extensoes_alvo,
                nome_branch=branch_a_ler
            )
            print("Leitura da branch bem-sucedida!")
            break 
        except GithubException as e:
            if e.status == 404:
                if tentativa < max_tentativas - 1:
                    print(f"Branch ainda não encontrada (erro 404). Aguardando {delay_entre_tentativas}s para a próxima tentativa...")
                    time.sleep(delay_entre_tentativas)
                else:
                    print("Número máximo de tentativas atingido. A branch realmente não foi encontrada ou está inacessível.")
                    raise e 
            else:
                print(f"Ocorreu um erro inesperado no GitHub que não é um 404: {e}")
                raise e
    
    if arquivos_encontrados is not None:
        print(f"\nLeitura concluída. Total de {len(arquivos_encontrados)} arquivos encontrados.")
    
    return arquivos_encontrados


