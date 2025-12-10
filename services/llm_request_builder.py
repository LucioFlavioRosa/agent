from typing import Dict, Any
from models.mcp_request import MCPRequest
from models.task_config import TaskConfig

class LLMRequestBuilder:
    @staticmethod
    def build_request(mcp_request: MCPRequest, task_config: TaskConfig, instrucoes_padrao: str) -> Dict[str, Any]:
        return {
            'project_id': mcp_request.project_id,
            'analysis_type': mcp_request.analysis_type,
            'instrucoes_extras': mcp_request.instrucoes_extras,
            'arquivo_docx': mcp_request.arquivo_docx,
            'nome_projeto': mcp_request.nome_projeto,
            'usuario_executor': mcp_request.usuario_executor,
            'model_name': task_config.model_name,
            'instrucoes_padrao': instrucoes_padrao
        }
