class ReaderGeral:
    def __init__(self, repository_provider, cache_service=None):
        self.repository_provider = repository_provider
        self.cache_service = cache_service

    def read_files(self, repository_type, repo_name, branch_name, file_paths):
        result = {}
        for file_path in file_paths:
            cache_key = f"repo_files:{repository_type}:{repo_name}:{branch_name}:{file_path}"
            file_content = None
            cache_hit = False
            if self.cache_service:
                cached = self.cache_service.get(cache_key)
                if cached is not None:
                    file_content = cached
                    cache_hit = True
                    print(f"[ReaderGeral] Cache HIT: {cache_key}")
                else:
                    print(f"[ReaderGeral] Cache MISS: {cache_key}")
            if file_content is None:
                file_content = self.repository_provider.read_file(branch_name, file_path)
                if self.cache_service:
                    self.cache_service.set(cache_key, file_content, ttl=3600)
            result[file_path] = file_content
        return result
