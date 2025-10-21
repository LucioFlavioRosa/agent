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

    # ... outras funções ...

    def criar_multiplas_tarefas(self, tarefas: List[Any], epico_nome: str) -> List[Dict[str, Any]]:
        resultados = []
        print(f"[AzureBoardsService] Iniciando criação de múltiplas tarefas para epico_nome='{epico_nome}'. Total de tarefas: {len(tarefas)}")
        for tarefa in tarefas:
            print(f"[AzureBoardsService] Tentando criar tarefa: id='{getattr(tarefa, 'id', None)}', titulo='{getattr(tarefa, 'titulo_tarefa', None)}', epico_nome='{epico_nome}'")
            resultado = self.criar_card_tarefa(tarefa, epico_nome)
            if resultado.get('id'):
                print(f"[AzureBoardsService] Tarefa criada com sucesso: id={resultado.get('id')}, titulo={resultado.get('titulo')}")
            else:
                print(f"[AzureBoardsService] Falha ao criar tarefa: titulo={resultado.get('titulo')}, erro={resultado.get('erro')}")
            resultados.append(resultado)
        print(f"[AzureBoardsService] Total de tarefas criadas (sucesso): {len([r for r in resultados if r.get('id')])}. Total de falhas: {len([r for r in resultados if r.get('erro')])}")
        return resultados
