class ProjectTracker:
    def __init__(self):
        self._memory = {}

    def set_status(self, project_id, status):
        self._memory[f"status:{project_id}"] = status

    def get_status(self, project_id):
        return self._memory.get(f"status:{project_id}")

    def set_result(self, project_id, result):
        self._memory[f"result:{project_id}"] = result

    def get_result(self, project_id):
        return self._memory.get(f"result:{project_id}")
