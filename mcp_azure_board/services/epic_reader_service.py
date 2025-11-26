from typing import Optional
from services.azure_board_service import AzureBoardService

class EpicReaderService:
    @staticmethod
    def get_epic_title(epic_id: str, organization: str, project: str) -> Optional[str]:
        """
        Busca o título do épico no Azure Board dado o epic_id, organização e projeto.
        """
        azure_board_service = AzureBoardService(organization=organization, project=project)
        epic_data = azure_board_service.read_epic(epic_id)
        if epic_data and isinstance(epic_data, dict):
            return epic_data.get('title')
        return None
