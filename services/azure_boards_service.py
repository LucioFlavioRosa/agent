import os
from typing import List, Dict, Any, Optional
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
        try:
            projects = self.connection.clients.get_core_client().get_projects()
            project_names = [p.name for p in projects]
            if self.project_name not in project_names:
                raise ValueError(f"Projeto '{self.project_name}' não encontrado na organização Azure DevOps.")
            print(f"[AzureBoardsService] Conexão estabelecida com sucesso. Projeto: {self.project_name}")
        except Exception as e:
            raise RuntimeError(f"Falha ao conectar ao Azure Boards ou validar projeto '{self.project_name}': {e}")

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
                        if getattr(state, 'category', None) == 'Proposed':
                            initial_state = state.name
                            break
                    else:
                        initial_state = states[0].name if states else 'New'
                    with AzureBoardsService._state_cache_lock:
                        AzureBoardsService._state_cache[cache_key] = initial_state
                    return initial_state
        except Exception as e:
            print(f"[AzureBoardsService] Erro ao obter estados válidos para {work_item_type}: {e}")
        with AzureBoardsService._state_cache_lock:
            AzureBoardsService._state_cache[cache_key] = 'New'
        return 'New'

    def buscar_epico_por_nome(self, nome_epico: str) -> Optional[int]:
        try:
            wiql_query = {
                "query": f"SELECT [System.Id], [System.Title], [System.CreatedDate] FROM WorkItems WHERE [System.TeamProject] = '{self.project_name}' AND [System.WorkItemType] = 'Epic' AND [System.Title] = '{nome_epico}' ORDER BY [System.CreatedDate] DESC"
            }
            result = self.wit_client.query_by_wiql(wiql_query["query"])
            work_items = result.work_items if hasattr(result, 'work_items') else []
            if not work_items:
                print(f"[AzureBoardsService] Nenhum épico encontrado com o nome '{nome_epico}' no projeto '{self.project_name}'.")
                return None
            epic_id = work_items[0].id
            print(f"[AzureBoardsService] Épico encontrado para nome '{nome_epico}': id={epic_id}")
            return epic_id
        except Exception as e:
            print(f"[AzureBoardsService] Erro ao buscar épico por nome '{nome_epico}': {e}")
            return None

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
        print(f"[AzureBoardsService] Preparando para criar Epic: Título='{epico.titulo}', Estado='{initial_state}', Projeto='{self.project_name}', Campos: {[{'path': op.path, 'value': op.value} for op in patch_document]}")
        try:
            new_work_item = self.wit_client.create_work_item(
                document=patch_document,
                project=self.project_name,
                type="Epic"
            )
            print(f"[AzureBoardsService] Epic criado com sucesso: id={new_work_item.id}, url={new_work_item.url}")
            return {
                "id": new_work_item.id,
                "url": new_work_item.url,
                "titulo": epico.titulo
            }
        except Exception as e:
            error_message = f"Erro ao criar card épico: {e} (Título='{epico.titulo}', Estado='{initial_state}')"
            print(f"[AzureBoardsService] {error_message}")
            return {"id": None, "url": None, "titulo": getattr(epico, 'titulo', '?'), "erro": error_message}

    def criar_multiplos_cards(self, epicos: List[Any]) -> List[Dict[str, Any]]:
        resultados = []
        for epico in epicos:
            try:
                resultado = self.criar_card_epico(epico)
                resultados.append(resultado)
            except Exception as e:
                error_message = f"Erro ao criar card para épico {getattr(epico, 'id', '?')}: {e}"
                print(f"[AzureBoardsService] {error_message}")
                resultados.append({"id": None, "url": None, "titulo": getattr(epico, 'titulo', '?'), "erro": error_message})
        return resultados

    def criar_card_tarefa(self, tarefa, epico_nome: str) -> Dict[str, Any]:
        initial_state = self._get_valid_initial_state('Task')
        epico_id = self.buscar_epico_por_nome(epico_nome)
        if not epico_id:
            error_message = f"Erro: Não foi possível encontrar o épico com nome '{epico_nome}' para criar a tarefa '{tarefa.titulo_tarefa}'."
            print(f"[AzureBoardsService] {error_message}")
            return {"id": None, "url": None, "titulo": tarefa.titulo_tarefa, "erro": error_message}
        patch_document = [
            JsonPatchOperation(op="add", path="/fields/System.Title", value=tarefa.titulo_tarefa),
            JsonPatchOperation(op="add", path="/fields/System.Description", value=tarefa.descricao_tarefa),
            JsonPatchOperation(op="add", path="/fields/System.State", value=initial_state)
        ]
        if tarefa.criterios_aceite:
            patch_document.append(JsonPatchOperation(op="add", path="/fields/Microsoft.VSTS.Common.AcceptanceCriteria", value=tarefa.criterios_aceite))
        if tarefa.estimativa_tempo:
            patch_document.append(JsonPatchOperation(op="add", path="/fields/Microsoft.VSTS.Scheduling.OriginalEstimate", value=tarefa.estimativa_tempo))
        relations = [
            {
                "rel": "System.LinkTypes.Hierarchy-Reverse",
                "url": f"{self.connection.base_url}/{self.project_name}/_apis/wit/workItems/{epico_id}",
                "attributes": {"comment": "Relacionamento com épico pai"}
            }
        ]
        print(f"[AzureBoardsService] Preparando para criar Task: Título='{tarefa.titulo_tarefa}', Estado='{initial_state}', Projeto='{self.project_name}', EpicNome='{epico_nome}', EpicId='{epico_id}', Campos: {[{'path': op.path, 'value': op.value} for op in patch_document]}")
        try:
            new_work_item = self.wit_client.create_work_item(
                document=patch_document,
                project=self.project_name,
                type="Task",
                relations=relations
            )
            print(f"[AzureBoardsService] Task criada com sucesso: id={new_work_item.id}, url={new_work_item.url}")
            return {
                "id": new_work_item.id,
                "url": new_work_item.url,
                "titulo": tarefa.titulo_tarefa
            }
        except Exception as e:
            error_message = f"Erro ao criar card tarefa: {e} (Título='{tarefa.titulo_tarefa}', Estado='{initial_state}', EpicNome='{epico_nome}', EpicId='{epico_id}')"
            print(f"[AzureBoardsService] {error_message}")
            return {"id": None, "url": None, "titulo": tarefa.titulo_tarefa, "erro": error_message}

    def criar_multiplas_tarefas(self, tarefas: List[Any], epico_nome: str) -> List[Dict[str, Any]]:
        resultados = []
        for tarefa in tarefas:
            resultado = self.criar_card_tarefa(tarefa, epico_nome)
            resultados.append(resultado)
        return resultados
