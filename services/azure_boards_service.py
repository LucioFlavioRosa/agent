import os
from typing import List, Dict, Any
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation

class AzureBoardsService:
    def __init__(self, organization_url: str, project_name: str, token: str):
        credentials = BasicAuthentication('', token)
        self.connection = Connection(base_url=organization_url, creds=credentials)
        self.project_name = project_name
        self.wit_client = self.connection.clients.get_work_item_tracking_client()

    def criar_card_epico(self, epico) -> Dict[str, Any]:
        patch_document = [
            JsonPatchOperation(op="add", path="/fields/System.Title", value=epico.titulo),
            JsonPatchOperation(op="add", path="/fields/System.State", value="To Do")
        ]
        descricao_html = f"<div><b>Objetivo de Negócio:</b> {epico.objetivo_negocio}<br><b>Critérios de Aceite / Atividades Chave:</b> {epico.criterios_aceite}<br><b>Perfis Envolvidos:</b> {epico.perfis_envolvidos}<br><b>Estimativa de Esforço:</b> {epico.estimativa_esforco}</div>"
        if epico.objetivo_negocio or epico.criterios_aceite or epico.perfis_envolvidos or epico.estimativa_esforco:
            patch_document.append(
                JsonPatchOperation(op="add", path="/fields/System.Description", value=descricao_html)
            )
        if epico.perfis_envolvidos:
            patch_document.append(
                JsonPatchOperation(op="add", path="/fields/System.Tags", value=epico.perfis_envolvidos)
            )
        try:
            new_work_item = self.wit_client.create_work_item(
                document=patch_document,
                project=self.project_name,
                type="Epic"
            )
            return {
                "id": new_work_item.id,
                "url": new_work_item.url,
                "titulo": epico.titulo
            }
        except Exception as e:
            print(f"Erro ao criar card épico: {e}")
            raise

    def criar_multiplos_cards(self, epicos: List[Any]) -> List[Dict[str, Any]]:
        resultados = []
        for epico in epicos:
            try:
                resultado = self.criar_card_epico(epico)
                resultados.append(resultado)
            except Exception as e:
                print(f"Erro ao criar card para épico {getattr(epico, 'id', '?')}: {e}")
                resultados.append({"id": None, "url": None, "titulo": getattr(epico, 'titulo', '?'), "erro": str(e)})
        return resultados
