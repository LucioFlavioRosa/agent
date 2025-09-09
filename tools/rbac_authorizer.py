import os
import json
from typing import List, Dict, Any

def get_allowed_resources(groups: List[str]) -> Dict[str, Any]:
    try:
        rbac_config_path = os.getenv('RBAC_CONFIG_PATH', 'rbac_config.json')
        
        if not os.path.exists(rbac_config_path):
            print(f"[RBAC] Arquivo de configuração não encontrado: {rbac_config_path}")
            return _get_default_permissions(groups)
        
        with open(rbac_config_path, 'r', encoding='utf-8') as f:
            rbac_config = json.load(f)
        
        allowed_tokens = set()
        allowed_repositories = set()
        
        for group in groups:
            group_config = rbac_config.get('groups', {}).get(group, {})
            
            group_tokens = group_config.get('tokens', [])
            group_repos = group_config.get('repositories', [])
            
            allowed_tokens.update(group_tokens)
            allowed_repositories.update(group_repos)
        
        result = {
            'tokens': list(allowed_tokens),
            'repositories': list(allowed_repositories)
        }
        
        print(f"[RBAC] Recursos permitidos para grupos {groups}: {result}")
        return result
        
    except Exception as e:
        print(f"[RBAC] Erro ao processar configuração RBAC: {e}")
        return _get_default_permissions(groups)

def _get_default_permissions(groups: List[str]) -> Dict[str, Any]:
    default_config = {
        'DevOps': {
            'tokens': ['github-token', 'gitlab-token', 'azure-token'],
            'repositories': ['*']
        },
        'Developers': {
            'tokens': ['github-token'],
            'repositories': ['org/dev-*', 'org/test-*']
        },
        'Analysts': {
            'tokens': ['github-token'],
            'repositories': ['org/analysis-*']
        }
    }
    
    allowed_tokens = set()
    allowed_repositories = set()
    
    for group in groups:
        group_config = default_config.get(group, {})
        
        group_tokens = group_config.get('tokens', [])
        group_repos = group_config.get('repositories', [])
        
        allowed_tokens.update(group_tokens)
        allowed_repositories.update(group_repos)
    
    result = {
        'tokens': list(allowed_tokens),
        'repositories': list(allowed_repositories)
    }
    
    print(f"[RBAC] Usando configuração padrão para grupos {groups}: {result}")
    return result

def is_repository_allowed(repo_name: str, allowed_repos: List[str]) -> bool:
    if '*' in allowed_repos:
        return True
    
    for allowed_pattern in allowed_repos:
        if allowed_pattern.endswith('*'):
            prefix = allowed_pattern[:-1]
            if repo_name.startswith(prefix):
                return True
        elif repo_name == allowed_pattern:
            return True
    
    return False