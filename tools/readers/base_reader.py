from typing import Dict, Optional, List, Union

class BaseReader:
    def __init__(self, repository_provider, cache_service=None):
        self.repository_provider = repository_provider
        self.cache_service = cache_service

    def _gerar_cache_key_lista_arquivos(self, platform: str, org: str, project: str, repo: str, branch: str) -> str:
        key = f"repo_file_list:{platform}:{org}/{project}/{repo}:{branch}"
        print(f"[CACHE][ListaArquivos] Chave gerada: {key}")
        return key

    def _gerar_cache_key_conteudo_arquivo(self, platform: str, org: str, project: str, repo: str, branch: str, file_path: str) -> str:
        key = f"repo_file_content:{platform}:{org}/{project}/{repo}:{branch}:{file_path}"
        print(f"[CACHE][ConteudoArquivo] Chave gerada: {key}")
        return key

    def _obter_lista_todos_arquivos_com_cache(self, platform: str, org: str, project: str, repo: str, branch: str, obter_lista_callback, ttl: int = 3600) -> List[str]:
        if self.cache_service:
            cache_key = self._gerar_cache_key_lista_arquivos(platform, org, project, repo, branch)
            cached = self.cache_service.get_cached_file_list(cache_key)
            if cached is not None:
                print(f"[CACHE][ListaArquivos] Cache HIT para {cache_key}")
                return cached
            print(f"[CACHE][ListaArquivos] Cache MISS para {cache_key}")
            lista = obter_lista_callback()
            self.cache_service.set_cached_file_list(cache_key, lista, ttl=ttl)
            return lista
        else:
            return obter_lista_callback()

    def _ler_conteudo_arquivo_com_cache(self, platform: str, org: str, project: str, repo: str, branch: str, file_path: str, ler_callback, ttl: int = 1800):
        if self.cache_service:
            cache_key = self._gerar_cache_key_conteudo_arquivo(platform, org, project, repo, branch, file_path)
            cached = self.cache_service.get(cache_key)
            if cached is not None:
                print(f"[CACHE][ConteudoArquivo] Cache HIT para {cache_key}")
                return cached
            print(f"[CACHE][ConteudoArquivo] Cache MISS para {cache_key}")
            conteudo = ler_callback()
            self.cache_service.set(cache_key, conteudo, ttl=ttl)
            return conteudo
        else:
            return ler_callback()
