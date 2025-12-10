from typing import Dict, Any
from domain.interfaces.board_reader_interface import IBoardReader
from services.azure_board_service import AzureBoardService

class AzureBoardReader(IBoardReader):
    def __init__(self, azure_board_service: AzureBoardService):
        self.azure_board_service = azure_board_service

    def read_epic(self, epic_id: str, organization: str, project: str) -> Dict[str, Any]:
        epic_data = self.azure_board_service.get_epic_data(epic_id=epic_id, organization=organization, project=project)
        if not epic_data:
            raise ValueError(f"Épico '{epic_id}' não encontrado no projeto '{project}' da organização '{organization}'.")
        return epic_data
