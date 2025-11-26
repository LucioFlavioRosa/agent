from typing import Dict, Any, Optional
from domain.interfaces.board_reader_interface import IBoardReader

class FeatureReaderService(IBoardReader):
    def __init__(self, azure_board_service):
        self.azure_board_service = azure_board_service

    def read_feature(self, feature_id: str) -> Dict[str, Any]:
        return self.azure_board_service.read_feature(feature_id)

    def read_features_from_epic(self, epic_id: str) -> Optional[list]:
        return self.azure_board_service.read_features_from_epic(epic_id)
