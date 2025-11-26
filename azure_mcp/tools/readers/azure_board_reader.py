class AzureBoardReader:
    def __init__(self, azure_board_service):
        self.azure_board_service = azure_board_service

    def read_epic(self, epic_id):
        return self.azure_board_service.read_feature(epic_id)

    def read_feature(self, feature_id):
        return self.azure_board_service.read_feature(feature_id)

    def read_task(self, task_id):
        # Implementação fictícia
        return {"task_id": task_id, "title": "Tarefa Exemplo"}
