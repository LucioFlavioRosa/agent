import logging
import uuid
from typing import Optional, Dict, Any, List

logger = logging.getLogger("ProjectStateService")

class ProjectStateService:
    _project_id_cache = {}

    @staticmethod
    def _normalize_nome_projeto(nome_projeto: Optional[str]) -> Optional[str]:
        if nome_projeto is None:
            return None
        return nome_projeto.strip().lower()

    @staticmethod
    async def _fetch_and_sanitize_projects(usuario_executor: str) -> List[Dict[str, Any]]:
        # Método mantido apenas para compatibilidade, mas não faz leitura de Blob Storage.
        # O backend não deve mais buscar projetos no Blob Storage.
        logger.info("[ProjectStateService] _fetch_and_sanitize_projects não implementa leitura de Blob Storage.")
        return []

    @staticmethod
    async def _get_project_id_by_name(usuario_executor: str, nome_projeto: str) -> Optional[str]:
        # Método mantido apenas para compatibilidade, mas não faz leitura de Blob Storage.
        logger.info("[ProjectStateService] _get_project_id_by_name não implementa leitura de Blob Storage.")
        return None

    # Todos os métodos relacionados a leitura e escrita de estados no Blob Storage foram removidos.
    # O backend não deve mais interagir com Blob Storage para persistência de estados.
