class CacheService:
    def __init__(self):
        self._repository_files_cache = {}
        self._file_list_cache = {}
        self._general_cache = {}
        
    def set_repository_files(self, job_id, files_dict):
        self._repository_files_cache[job_id] = files_dict
        
    def get_repository_files(self, job_id):
        return self._repository_files_cache.get(job_id)
        
    def set_file_list(self, job_id, file_list):
        self._file_list_cache[job_id] = file_list
        
    def get_file_list(self, job_id):
        return self._file_list_cache.get(job_id)
        
    def exists(self, job_id, key):
        if key == 'repository_files':
            return job_id in self._repository_files_cache
        if key == 'file_list':
            return job_id in self._file_list_cache
        return False

    def set_value(self, key, value):
        """Salva um par chave/valor genérico no cache."""
        self._general_cache[key] = value

    def get_value(self, key):
        """Recupera um valor genérico do cache pela chave."""
        return self._general_cache.get(key)
