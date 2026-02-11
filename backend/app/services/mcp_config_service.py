import os
import json
from typing import Optional
from backend.app.models.mcp_config_models import MCPConfigRegistry, MCPAgentConfig

class MCPConfigService:
    _config_cache: Optional[MCPConfigRegistry] = None

    @staticmethod
    def load_config(config_path: Optional[str] = None) -> MCPConfigRegistry:
        if config_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_path = os.path.join(base_dir, 'config', 'mcp_agents.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return MCPConfigRegistry.parse_obj(data)
        return MCPConfigRegistry(agents={})

    @classmethod
    def get_agent_config(cls, agent_name: str, config_path: Optional[str] = None) -> Optional[MCPAgentConfig]:
        if cls._config_cache is None:
            cls._config_cache = cls.load_config(config_path)
        return cls._config_cache.agents.get(agent_name)
