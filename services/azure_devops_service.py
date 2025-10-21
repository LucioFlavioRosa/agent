class AzureDevOpsService:
    def __init__(self):
        pass
    def create_epic(self, organization, project, board, title, objetivo_negocio=None, criterios_aceite=None, perfis_envolvidos=None, estimativa_esforco=None, description=None):
        epic_fields = {
            'title': title,
            'description': description if description is not None else objetivo_negocio,
            'objetivo_negocio': objetivo_negocio,
            'criterios_aceite': criterios_aceite,
            'perfis_envolvidos': perfis_envolvidos,
            'estimativa_esforco': estimativa_esforco
        }
        epic_id = self._create_work_item(organization, project, board, epic_fields)
        return epic_id
    def _create_work_item(self, organization, project, board, fields):
        return f"EPIC-{organization}-{project}-{fields['title']}"