class ProjectTracker:
    def __init__(self, redis_conn=None):
        self.redis_conn = redis_conn
        self._memory = {} if redis_conn is None else None

    def set_status(self, project_id, status):
        if self.redis_conn:
            self.redis_conn.set(f"project_status:{project_id}", status)
        else:
            self._memory[f"status:{project_id}"] = status

    def get_status(self, project_id):
        if self.redis_conn:
            val = self.redis_conn.get(f"project_status:{project_id}")
            return val.decode() if val else None
        else:
            return self._memory.get(f"status:{project_id}")

    def set_result(self, project_id, result):
        if self.redis_conn:
            self.redis_conn.set(f"project_result:{project_id}", result)
        else:
            self._memory[f"result:{project_id}"] = result

    def get_result(self, project_id):
        if self.redis_conn:
            val = self.redis_conn.get(f"project_result:{project_id}")
            return val.decode() if val else None
        else:
            return self._memory.get(f"result:{project_id}")
