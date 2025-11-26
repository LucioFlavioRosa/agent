class FeatureReaderService:
    def read_feature(self, feature_id, azure_board_service):
        # Lê dados da feature no Azure DevOps Board
        return azure_board_service.read_feature(feature_id)
