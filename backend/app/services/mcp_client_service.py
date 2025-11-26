import requests
from typing import Dict, Any

class McpClientService:
    def __init__(self, mcp_url: str = "http://mcp_azure_board:8000"):
        self.mcp_url = mcp_url.rstrip('/')

    def start_epic_analysis(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Envia uma requisição POST para o MCP Azure Board para iniciar análise de épicos.
        Retorna o JSON de resposta ou lança exceção em caso de falha.
        """
        url = f"{self.mcp_url}/start-analysis"
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            # Logar erro se necessário
            raise RuntimeError(f"Erro ao comunicar com MCP Azure Board: {e}")
