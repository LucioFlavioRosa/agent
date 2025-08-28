# Arquivo: tools/user_token_resolver.py
# Módulo para resolução da cadeia usuário → grupo → token via Redis

import os
import redis
from typing import Optional

class UserTokenResolver:
    """
    Classe responsável por resolver a cadeia usuário → grupo → token consultando Redis.
    
    Esta classe implementa a lógica de associação entre usuários, grupos e tokens,
    permitindo que o sistema determine qual token usar para um usuário específico
    sem alterar o código legado existente.
    
    Convenção de Chaves Redis:
    - Usuário → Grupo: mcp_user_group:{username}
    - Grupo → Token: mcp_group_token:{groupname}
    
    Attributes:
        redis_client: Cliente Redis configurado para consultas
        USER_GROUP_PREFIX (str): Prefixo para chaves de associação usuário-grupo
        GROUP_TOKEN_PREFIX (str): Prefixo para chaves de associação grupo-token
    
    Example:
        >>> resolver = UserTokenResolver()
        >>> token_name = resolver.get_token_name("joao.silva")
        >>> print(f"Token para usuário: {token_name}")
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Inicializa o resolver com conexão Redis.
        
        Args:
            redis_url (Optional[str]): URL de conexão Redis. Se None, usa REDIS_URL do ambiente
        
        Raises:
            ValueError: Se REDIS_URL não estiver configurada no ambiente
            redis.exceptions.ConnectionError: Se não conseguir conectar ao Redis
        """
        self.redis_url = redis_url or os.environ.get("REDIS_URL")
        if not self.redis_url:
            raise ValueError("A variável de ambiente REDIS_URL não foi configurada.")
        
        print(f"Conectando ao Redis para resolução de tokens via URL: {self.redis_url.split('@')[-1]}")
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
        
        # Convenção de prefixos para organização das chaves
        self.USER_GROUP_PREFIX = "mcp_user_group"
        self.GROUP_TOKEN_PREFIX = "mcp_group_token"
    
    def get_group_for_user(self, username: str) -> Optional[str]:
        """
        Obtém o grupo associado a um usuário específico.
        
        Args:
            username (str): Nome do usuário a ser consultado
        
        Returns:
            Optional[str]: Nome do grupo associado ou None se não encontrado
        
        Raises:
            redis.exceptions.RedisError: Se houver erro na comunicação com Redis
        """
        if not username or not username.strip():
            raise ValueError("Nome de usuário não pode estar vazio.")
        
        key = f"{self.USER_GROUP_PREFIX}:{username.strip()}"
        
        try:
            group = self.redis_client.get(key)
            if group:
                print(f"Usuário '{username}' associado ao grupo '{group}'.")
            else:
                print(f"AVISO: Usuário '{username}' não possui grupo associado no Redis.")
            return group
        except redis.exceptions.RedisError as e:
            print(f"ERRO CRÍTICO ao consultar grupo para usuário '{username}': {e}")
            raise
    
    def get_token_for_group(self, groupname: str) -> Optional[str]:
        """
        Obtém o nome do token associado a um grupo específico.
        
        Args:
            groupname (str): Nome do grupo a ser consultado
        
        Returns:
            Optional[str]: Nome do token associado ou None se não encontrado
        
        Raises:
            redis.exceptions.RedisError: Se houver erro na comunicação com Redis
        """
        if not groupname or not groupname.strip():
            raise ValueError("Nome do grupo não pode estar vazio.")
        
        key = f"{self.GROUP_TOKEN_PREFIX}:{groupname.strip()}"
        
        try:
            token_name = self.redis_client.get(key)
            if token_name:
                print(f"Grupo '{groupname}' associado ao token '{token_name}'.")
            else:
                print(f"AVISO: Grupo '{groupname}' não possui token associado no Redis.")
            return token_name
        except redis.exceptions.RedisError as e:
            print(f"ERRO CRÍTICO ao consultar token para grupo '{groupname}': {e}")
            raise
    
    def get_token_name(self, username: str) -> str:
        """
        Resolve a cadeia completa usuário → grupo → token.
        
        Este é o método principal que implementa a lógica de resolução completa,
        seguindo a cadeia de associações para determinar qual token usar.
        
        Args:
            username (str): Nome do usuário para resolução do token
        
        Returns:
            str: Nome do token a ser usado para o usuário
        
        Raises:
            ValueError: Se usuário não estiver associado a grupo ou grupo não tiver token
            redis.exceptions.RedisError: Se houver erro na comunicação com Redis
        
        Note:
            Este método garante que toda a cadeia de associação seja válida,
            falhando rapidamente se algum elo estiver quebrado.
        """
        print(f"\n--- Iniciando resolução de token para usuário: '{username}' ---")
        
        # Etapa 1: Usuário → Grupo
        group = self.get_group_for_user(username)
        if not group:
            raise ValueError(f"Usuário '{username}' não está associado a nenhum grupo no Redis.")
        
        # Etapa 2: Grupo → Token
        token_name = self.get_token_for_group(group)
        if not token_name:
            raise ValueError(f"Grupo '{group}' não está associado a nenhum token no Redis.")
        
        print(f"SUCESSO: Usuário '{username}' → Grupo '{group}' → Token '{token_name}'")
        print("--- Resolução de token concluída ---\n")
        
        return token_name
    
    def validate_user_token_chain(self, username: str) -> dict:
        """
        Valida toda a cadeia de associação e retorna informações detalhadas.
        
        Método utilitário para debugging e validação de configurações,
        retornando informações estruturadas sobre o estado da cadeia.
        
        Args:
            username (str): Nome do usuário para validação
        
        Returns:
            dict: Informações detalhadas sobre a cadeia de associação:
                - valid (bool): Se a cadeia está válida
                - username (str): Nome do usuário consultado
                - group (Optional[str]): Grupo associado
                - token_name (Optional[str]): Nome do token
                - error (Optional[str]): Mensagem de erro se inválida
        """
        result = {
            "valid": False,
            "username": username,
            "group": None,
            "token_name": None,
            "error": None
        }
        
        try:
            # Valida usuário → grupo
            group = self.get_group_for_user(username)
            result["group"] = group
            
            if not group:
                result["error"] = f"Usuário '{username}' não possui grupo associado"
                return result
            
            # Valida grupo → token
            token_name = self.get_token_for_group(group)
            result["token_name"] = token_name
            
            if not token_name:
                result["error"] = f"Grupo '{group}' não possui token associado"
                return result
            
            # Cadeia válida
            result["valid"] = True
            return result
            
        except Exception as e:
            result["error"] = str(e)
            return result


# Funções utilitárias para uso procedural (compatibilidade e conveniência)

def resolve_token_name_for_user(username: str, redis_url: Optional[str] = None) -> str:
    """
    Função utilitária procedural para resolução rápida de token.
    
    Esta função oferece uma interface simples para casos onde não é necessário
    manter uma instância da classe UserTokenResolver.
    
    Args:
        username (str): Nome do usuário para resolução
        redis_url (Optional[str]): URL Redis customizada (opcional)
    
    Returns:
        str: Nome do token a ser usado
    
    Raises:
        ValueError: Se a cadeia de associação estiver incompleta
        redis.exceptions.RedisError: Se houver erro de comunicação com Redis
    
    Example:
        >>> token_name = resolve_token_name_for_user("maria.santos")
        >>> print(f"Token: {token_name}")
    """
    resolver = UserTokenResolver(redis_url)
    return resolver.get_token_name(username)

def get_group_for_user(username: str, redis_url: Optional[str] = None) -> Optional[str]:
    """
    Função utilitária para obter apenas o grupo de um usuário.
    
    Útil para casos onde apenas a primeira parte da cadeia é necessária
    ou para debugging de configurações.
    
    Args:
        username (str): Nome do usuário
        redis_url (Optional[str]): URL Redis customizada (opcional)
    
    Returns:
        Optional[str]: Nome do grupo ou None se não encontrado
    
    Example:
        >>> group = get_group_for_user("carlos.lima")
        >>> if group:
        ...     print(f"Usuário pertence ao grupo: {group}")
    """
    resolver = UserTokenResolver(redis_url)
    return resolver.get_group_for_user(username)

def get_token_for_group(groupname: str, redis_url: Optional[str] = None) -> Optional[str]:
    """
    Função utilitária para obter o token de um grupo específico.
    
    Útil para casos onde o grupo já é conhecido ou para validação
    de configurações de grupos.
    
    Args:
        groupname (str): Nome do grupo
        redis_url (Optional[str]): URL Redis customizada (opcional)
    
    Returns:
        Optional[str]: Nome do token ou None se não encontrado
    
    Example:
        >>> token = get_token_for_group("desenvolvimento")
        >>> if token:
        ...     print(f"Grupo usa o token: {token}")
    """
    resolver = UserTokenResolver(redis_url)
    return resolver.get_token_for_group(groupname)

def validate_user_setup(username: str, redis_url: Optional[str] = None) -> dict:
    """
    Função utilitária para validação completa da configuração de um usuário.
    
    Ideal para debugging, testes e validação de configurações antes
    de executar operações que dependem da resolução de tokens.
    
    Args:
        username (str): Nome do usuário para validação
        redis_url (Optional[str]): URL Redis customizada (opcional)
    
    Returns:
        dict: Informações detalhadas sobre a configuração do usuário
    
    Example:
        >>> status = validate_user_setup("admin")
        >>> if status["valid"]:
        ...     print(f"Usuário configurado corretamente: {status['token_name']}")
        ... else:
        ...     print(f"Erro na configuração: {status['error']}")
    """
    resolver = UserTokenResolver(redis_url)
    return resolver.validate_user_token_chain(username)
