class EpicReaderService:
    def read_epic(self, epic_id, azure_board_service):
        # Lê dados do épico no Azure DevOps Board
        return azure_board_service.read_feature(epic_id)
