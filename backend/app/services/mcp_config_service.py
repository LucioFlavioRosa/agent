import os
import json
from typing import Optional
from backend.app.models.mcp_config_models import MCPConfigRegistry

class MCPConfigService:
    @staticmethod
    def load_config(config_path: Optional[str] = None) -> MCPConfigRegistry:
        if config_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_path = os.path.join(base_dir, 'config', 'mcp_agents.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return MCPConfigRegistry.parse_obj(data)
        # Fallback: retorna config vazia
        return MCPConfigRegistry(agents={})
