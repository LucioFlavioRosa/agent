import time
import yaml
import os
from typing import Dict, Optional, List, Union, Any
from domain.interfaces.repository_reader_interface import IRepositoryReader
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.github_repository_provider import GitHubRepositoryProvider
from tools.conectores.conexao_geral import ConexaoGeral
from .github_reader import GitHubReader
from .gitlab_reader import GitLabReader
from .azure_reader import AzureReader

class ReaderGeral(IRepositoryReader):
    def __init__(self, repository_provider: Optional[IRepositoryProvider] = None, cache_service: Optional[Any] = None):
        self.repository_provider = repository_provider or GitHubRepositoryProvider()
        self._mapeamento_tipo_extensoes = self._carregar_config_workflows()
        self.github_reader = GitHubReader(repository_provider)
        self.gitlab_reader = GitLabReader(repository_provider)
        self.azure_reader = AzureReader(repository_provider)
        self.cache_service = cache_service

    def _carregar_config_workflows(self):
        try:
            script_dir = os.path.dirname(__file__)
            project_root = os.path.abspath(os.path.join(script_dir, '../..'))
            yaml_path = os.path.join(project_root, 'workflows.yaml')
            with open(yaml_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            mapeamento_expandido = {}
            for workflow_name, data in config.items():
                extensions = data.get('extensions', [])
                if not extensions:
                    continue
                mapeamento_expandido[workflow_name.lower()] = extensions
                for step in data.get('steps', []):
                    params = step.get('params', {})
                    tipo_analise_step = params.get('tipo_analise')
                    if tipo_analise_step:
                        mapeamento_expandido[tipo_analise_step.lower()] = extensions
            return mapeamento_expandido
        except Exception as e:
            print(f"ERRO INESPERADO ao carregar workflows: {e}")
            raise

    def read_repository(
        self, 
        nome_repo: str, 
        tipo_analise: str,
        repository_type: str,
        nome_branch: str = None,
        arquivos_especificos: Optional[List[str]] = None,
        retornar_lista_arquivos: bool = False
    ) -> Union[Dict[str, str], Dict[str, Union[Dict[str, str], List[str]]]]:
        
        print(f"[Reader Geral] Iniciando leitura. Repositório: {nome_repo}, Tipo: {repository_type}")
        
        # --- SETUP INICIAL ---
        conexao_geral = ConexaoGeral.create_with_defaults()
        repositorio = conexao_geral.connection(repositorio=nome_repo, repository_type=repository_type, repository_provider=self.repository_provider)
        branch_a_ler = nome_branch or repositorio.get('default_branch', 'main') if isinstance(repositorio, dict) else nome_branch or repositorio.default_branch
        cache_ttl = 3600
        
        # --- MELHORIA: 1. Determinar o leitor correto UMA VEZ ---
        leitor = None
        if repository_type == 'azure':
            leitor = self.azure_reader
        elif repository_type == 'gitlab':
            leitor = self.gitlab_reader
        else: # Assume GitHub
            leitor = self.github_reader
    
        conteudo_dos_arquivos = {}
        lista_final_de_arquivos = None
    
        # --- 2. Lógica de Cache para a LISTA de arquivos (se necessário) ---
        if retornar_lista_arquivos and self.cache_service:
            lista_arquivos_cache_key = f"repo_file_list:{repository_type}:{nome_repo}:{branch_a_ler}"
            lista_final_de_arquivos = self.cache_service.get(lista_arquivos_cache_key)
    
            if lista_final_de_arquivos is not None:
                print(f"[Reader Geral] CACHE HIT (lista de arquivos): {lista_arquivos_cache_key}")
            else:
                print(f"[Reader Geral] CACHE MISS (lista de arquivos): {lista_arquivos_cache_key}")
                # Usa o 'leitor' correto para buscar os dados
                lista_final_de_arquivos = leitor._obter_lista_todos_arquivos(repositorio, branch_a_ler)
                
                if lista_final_de_arquivos:
                    self.cache_service.set(lista_arquivos_cache_key, lista_final_de_arquivos, ttl=cache_ttl)
                    print(f"[Reader Geral] Lista de arquivos salva no cache.")
    
        # --- 3. Lógica de Cache para o CONTEÚDO dos arquivos ---
        arquivos_para_ler_conteudo = arquivos_especificos or []
        if not arquivos_especificos:
            # Se não há arquivos específicos, determina quais ler com base na extensão
            extensoes_alvo = self._mapeamento_tipo_extensoes.get(tipo_analise.lower())
            if not extensoes_alvo:
                raise ValueError(f"Tipo de análise '{tipo_analise}' não encontrado ou sem extensões definidas.")
            
            # Se já temos a lista de arquivos (do passo 2), filtramos a partir dela
            if lista_final_de_arquivos:
                arquivos_para_ler_conteudo = [f for f in lista_final_de_arquivos if any(f.endswith(ext) for ext in extensoes_alvo)]
            else:
                # Se não, teremos que buscar a lista agora (mesmo que não seja para retornar)
                print("[Reader Geral] Buscando lista de arquivos para filtrar por extensão...")
                lista_completa_temp = leitor._obter_lista_todos_arquivos(repositorio, branch_a_ler)
                arquivos_para_ler_conteudo = [f for f in lista_completa_temp if any(f.endswith(ext) for ext in extensoes_alvo)]
    
        # Loop principal para ler o conteúdo (seja de arquivos_especificos ou da lista filtrada)
        if arquivos_para_ler_conteudo and self.cache_service:
            print(f"[Reader Geral] Verificando cache/lendo conteúdo de {len(arquivos_para_ler_conteudo)} arquivos.")
            for file_path in arquivos_para_ler_conteudo:
                cache_key = f"repo_files:{repository_type}:{nome_repo}:{branch_a_ler}:{file_path}"
                cached_content = self.cache_service.get(cache_key)
                
                if cached_content is not None:
                    print(f"[Reader Geral] CACHE HIT (conteúdo): {file_path}")
                    conteudo_dos_arquivos[file_path] = cached_content
                else:
                    print(f"[Reader Geral] CACHE MISS (conteúdo): {file_path}")
                    # Usa o 'leitor' correto para buscar o conteúdo do arquivo
                    file_content = leitor.read_single_file(repositorio, file_path, branch_a_ler)
                    
                    if file_content is not None:
                        conteudo_dos_arquivos[file_path] = file_content
                        self.cache_service.set(cache_key, file_content, ttl=cache_ttl)
        else:
             # Fallback para o caso de não usar cache (não deve acontecer no seu fluxo atual)
             print("[Reader Geral] AVISO: Cache service não disponível. Delegando leitura completa.")
             return leitor.read_repository_internal(repositorio, tipo_analise, nome_branch, arquivos_especificos, self._mapeamento_tipo_extensoes, retornar_lista_arquivos)
    
        # --- 4. Montar o Resultado Final ---
        if retornar_lista_arquivos:
            return {'codigo': conteudo_dos_arquivos, 'lista_arquivos': lista_final_de_arquivos or []}
        else:
            return conteudo_dos_arquivos
