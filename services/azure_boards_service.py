import os
from typing import List, Dict, Any
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation
import threading

class AzureBoardsService:
    _state_cache_lock = threading.Lock()
    _state_cache: Dict[str, str] = {}

    def __init__(self, organization_url: str, project_name: str, token: str):
        credentials = BasicAuthentication('', token)
        self.connection = Connection(base_url=organization_url, creds=credentials)
        self.project_name = project_name
        self.wit_client = self.connection.clients.get_work_item_tracking_client()

    def _get_valid_initial_state(self, work_item_type: str) -> str:
        cache_key = f"{self.project_name}:{work_item_type}"
        with AzureBoardsService._state_cache_lock:
            if cache_key in AzureBoardsService._state_cache:
                return AzureBoardsService._state_cache[cache_key]
        try:
            work_item_types = self.wit_client.get_work_item_types(self.project_name)
            for wit in work_item_types:
                if wit.name.lower() == work_item_type.lower():
                    states = self.wit_client.get_work_item_type_states(self.project_name, wit.name)
                    for state in states:
                        # Azure DevOps: o estado inicial geralmente tem category='Proposed'
                        if getattr(state, 'category', None) == 'Proposed':
                            initial_state = state.name
                            break
                    else:
                        # fallback: pega o primeiro estado
                        initial_state = states[0].name if states else 'New'
                    with AzureBoardsService._state_cache_lock:
                        AzureBoardsService._state_cache[cache_key] = initial_state
                    return initial_state
        except Exception as e:
            print(f"Erro ao obter estados válidos para {work_item_type}: {e}")
        # fallback seguro
        with AzureBoardsService._state_cache_lock:
            AzureBoardsService._state_cache[cache_key] = 'New'
        return 'New'

    def criar_card_epico(self, epico) -> Dict[str, Any]:
        initial_state = self._get_valid_initial_state('Epic')
        patch_document = [
            JsonPatchOperation(op="add", path="/fields/System.Title", value=epico.titulo),
            JsonPatchOperation(op="add", path="/fields/System.State", value=initial_state)
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

    def criar_card_tarefa(self, tarefa, epico_id: int) -> Dict[str, Any]:
        initial_state = self._get_valid_initial_state('Task')
        patch_document = [
            JsonPatchOperation(op="add", path="/fields/System.Title", value=tarefa.titulo_tarefa),
            JsonPatchOperation(op="add", path="/fields/System.Description", value=tarefa.descricao_tarefa),
            JsonPatchOperation(op="add", path="/fields/System.State", value=initial_state)
        ]
        if tarefa.criterios_aceite:
            patch_document.append(JsonPatchOperation(op="add", path="/fields/Microsoft.VSTS.Common.AcceptanceCriteria", value=tarefa.criterios_aceite))
        if tarefa.estimativa_tempo:
            patch_document.append(JsonPatchOperation(op="add", path="/fields/Microsoft.VSTS.Scheduling.OriginalEstimate", value=tarefa.estimativa_tempo))
        # Relacionamento com épico pai
        relations = [
            {
                "rel": "System.LinkTypes.Hierarchy-Reverse",
                "url": f"{self.connection.base_url}/{self.project_name}/_apis/wit/workItems/{epico_id}",
                "attributes": {"comment": "Relacionamento com épico pai"}
            }
        ]
        try:
            new_work_item = self.wit_client.create_work_item(
                document=patch_document,
                project=self.project_name,
                type="Task",
                relations=relations
            )
            return {
                "id": new_work_item.id,
                "url": new_work_item.url,
                "titulo": tarefa.titulo_tarefa
            }
        except Exception as e:
            print(f"Erro ao criar card tarefa: {e}")
            return {"id": None, "url": None, "titulo": tarefa.titulo_tarefa, "erro": str(e)}

    def criar_multiplas_tarefas(self, tarefas: List[Any], epico_id: int) -> List[Dict[str, Any]]:
        resultados = []
        for tarefa in tarefas:
            resultado = self.criar_card_tarefa(tarefa, epico_id)
            resultados.append(resultado)
        return resultados
