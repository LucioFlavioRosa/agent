from abc import ABC, abstractmethod

class IAzureDevOpsService(ABC):
    @abstractmethod
    def create_epic(self, organization, project, board, title, description):
        pass

    @abstractmethod
    def create_task(self, organization, project, board, epic_id, titulo, descricao, criterios_de_aceite, perfis_sugeridos, estimativa_sp):
        pass
