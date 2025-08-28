import redis
import os
import json
from typing import Optional, Dict, List
from domain.interfaces.user_token_repository_interface import IUserTokenRepository

class RedisUserTokenRepository(IUserTokenRepository):
    """
    Implementação concreta de IUserTokenRepository usando Redis como backend.
    
    Esta implementação utiliza Redis para armazenar as associações entre usuários,
    grupos e tokens de repositório. Usa estruturas de dados Redis otimizadas para
    consultas eficientes e escalabilidade.
    
    Estrutura de Dados no Redis:
    - user_groups:{user_id} → Set de group_ids
    - group_tokens:{group_id} → Hash {empresa: token}
    - all_groups → Set de todos os group_ids
    
    Características:
    - Operações atômicas para consistência
    - Suporte a TTL para expiração automática (futuro)
    - Estruturas otimizadas para consultas rápidas
    - Compatível com Redis Cluster
    
    Example:
        >>> repo = RedisUserTokenRepository()
        >>> repo.add_user_to_group("alice", "frontend-team")
        >>> repo.set_group_token("frontend-team", "acme-corp", "ghp_xyz123")
        >>> token = repo.get_token_for_user("alice", "acme-corp")
        >>> print(token)  # "ghp_xyz123"
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Inicializa o repositório com conexão Redis.
        
        Args:
            redis_url (Optional[str]): URL de conexão Redis. Se None, usa
                variável de ambiente REDIS_URL
        
        Raises:
            ValueError: Se REDIS_URL não estiver configurada e redis_url for None
            ConnectionError: Se não conseguir conectar ao Redis
        """
        url = redis_url or os.getenv("REDIS_URL")
        if not url:
            raise ValueError("REDIS_URL não configurada e redis_url não fornecida.")
        
        try:
            self.redis_client = redis.from_url(url, decode_responses=True)
            # Testa a conexão
            self.redis_client.ping()
            print(f"RedisUserTokenRepository: Conectado ao Redis via {url.split('@')[-1]}")
        except redis.exceptions.RedisError as e:
            raise ConnectionError(f"Falha ao conectar ao Redis: {e}") from e
        
        # Prefixos para organização das chaves
        self.USER_GROUPS_PREFIX = "user_groups"
        self.GROUP_TOKENS_PREFIX = "group_tokens"
        self.ALL_GROUPS_KEY = "all_groups"
    
    def _user_groups_key(self, user_id: str) -> str:
        """Gera chave Redis para grupos de um usuário."""
        return f"{self.USER_GROUPS_PREFIX}:{user_id}"
    
    def _group_tokens_key(self, group_id: str) -> str:
        """Gera chave Redis para tokens de um grupo."""
        return f"{self.GROUP_TOKENS_PREFIX}:{group_id}"
    
    def add_user_to_group(self, user_id: str, group_id: str) -> bool:
        """
        Associa um usuário a um grupo usando operações atômicas Redis.
        
        Implementação:
        1. Adiciona group_id ao set de grupos do usuário
        2. Adiciona group_id ao set global de grupos
        3. Ambas operações são atômicas via pipeline
        
        Args:
            user_id (str): Identificador único do usuário
            group_id (str): Identificador único do grupo
            
        Returns:
            bool: True se associação foi criada, False se já existia
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id não pode ser vazio")
        if not group_id or not group_id.strip():
            raise ValueError("group_id não pode ser vazio")
        
        try:
            # Pipeline para operações atômicas
            pipe = self.redis_client.pipeline()
            user_key = self._user_groups_key(user_id)
            
            # Verifica se associação já existe
            if self.redis_client.sismember(user_key, group_id):
                return False  # Já existe
            
            # Adiciona usuário ao grupo e grupo à lista global
            pipe.sadd(user_key, group_id)
            pipe.sadd(self.ALL_GROUPS_KEY, group_id)
            pipe.execute()
            
            print(f"Usuário '{user_id}' adicionado ao grupo '{group_id}'")
            return True
            
        except redis.exceptions.RedisError as e:
            raise ConnectionError(f"Erro Redis ao adicionar usuário ao grupo: {e}") from e
    
    def remove_user_from_group(self, user_id: str, group_id: str) -> bool:
        """
        Remove a associação entre usuário e grupo.
        
        Args:
            user_id (str): Identificador único do usuário
            group_id (str): Identificador único do grupo
            
        Returns:
            bool: True se associação foi removida, False se não existia
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id não pode ser vazio")
        if not group_id or not group_id.strip():
            raise ValueError("group_id não pode ser vazio")
        
        try:
            user_key = self._user_groups_key(user_id)
            removed_count = self.redis_client.srem(user_key, group_id)
            
            if removed_count > 0:
                print(f"Usuário '{user_id}' removido do grupo '{group_id}'")
                return True
            return False
            
        except redis.exceptions.RedisError as e:
            raise ConnectionError(f"Erro Redis ao remover usuário do grupo: {e}") from e
    
    def set_group_token(self, group_id: str, empresa: str, token: str) -> bool:
        """
        Define token de repositório para um grupo em uma empresa específica.
        
        Implementação:
        1. Armazena token em hash Redis: group_tokens:{group_id} → {empresa: token}
        2. Adiciona grupo ao set global de grupos
        3. Operações atômicas via pipeline
        
        Args:
            group_id (str): Identificador único do grupo
            empresa (str): Nome da empresa/organização
            token (str): Token de acesso ao repositório
            
        Returns:
            bool: True sempre (Redis HSET sempre sucede)
        """
        if not group_id or not group_id.strip():
            raise ValueError("group_id não pode ser vazio")
        if not empresa or not empresa.strip():
            raise ValueError("empresa não pode ser vazia")
        if not token or not token.strip():
            raise ValueError("token não pode ser vazio")
        
        try:
            # Pipeline para operações atômicas
            pipe = self.redis_client.pipeline()
            tokens_key = self._group_tokens_key(group_id)
            
            # Define token e registra grupo globalmente
            pipe.hset(tokens_key, empresa, token)
            pipe.sadd(self.ALL_GROUPS_KEY, group_id)
            pipe.execute()
            
            print(f"Token definido para grupo '{group_id}' na empresa '{empresa}'")
            return True
            
        except redis.exceptions.RedisError as e:
            raise ConnectionError(f"Erro Redis ao definir token do grupo: {e}") from e
    
    def get_token_for_user(self, user_id: str, empresa: str) -> Optional[str]:
        """
        Obtém token de repositório para usuário em empresa específica.
        
        Algoritmo:
        1. Busca todos os grupos do usuário
        2. Para cada grupo, verifica se tem token para a empresa
        3. Retorna o primeiro token encontrado
        
        Args:
            user_id (str): Identificador único do usuário
            empresa (str): Nome da empresa/organização
            
        Returns:
            Optional[str]: Token se encontrado, None caso contrário
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id não pode ser vazio")
        if not empresa or not empresa.strip():
            raise ValueError("empresa não pode ser vazia")
        
        try:
            # Busca grupos do usuário
            user_groups = self.get_user_groups(user_id)
            if not user_groups:
                return None
            
            # Busca token em cada grupo
            for group_id in user_groups:
                tokens_key = self._group_tokens_key(group_id)
                token = self.redis_client.hget(tokens_key, empresa)
                if token:
                    print(f"Token encontrado para usuário '{user_id}' na empresa '{empresa}' via grupo '{group_id}'")
                    return token
            
            print(f"Nenhum token encontrado para usuário '{user_id}' na empresa '{empresa}'")
            return None
            
        except redis.exceptions.RedisError as e:
            raise ConnectionError(f"Erro Redis ao buscar token do usuário: {e}") from e
    
    def get_user_groups(self, user_id: str) -> List[str]:
        """
        Obtém lista de grupos de um usuário.
        
        Args:
            user_id (str): Identificador único do usuário
            
        Returns:
            List[str]: Lista de identificadores de grupos
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id não pode ser vazio")
        
        try:
            user_key = self._user_groups_key(user_id)
            groups = list(self.redis_client.smembers(user_key))
            return sorted(groups)  # Retorna ordenado para consistência
            
        except redis.exceptions.RedisError as e:
            raise ConnectionError(f"Erro Redis ao buscar grupos do usuário: {e}") from e
    
    def get_group_tokens(self, group_id: str) -> Dict[str, str]:
        """
        Obtém todos os tokens de um grupo, organizados por empresa.
        
        Args:
            group_id (str): Identificador único do grupo
            
        Returns:
            Dict[str, str]: Mapeamento empresa → token
        """
        if not group_id or not group_id.strip():
            raise ValueError("group_id não pode ser vazio")
        
        try:
            tokens_key = self._group_tokens_key(group_id)
            tokens = self.redis_client.hgetall(tokens_key)
            return dict(tokens)  # Converte para dict Python padrão
            
        except redis.exceptions.RedisError as e:
            raise ConnectionError(f"Erro Redis ao buscar tokens do grupo: {e}") from e
    
    def list_all_groups(self) -> List[str]:
        """
        Lista todos os grupos existentes no sistema.
        
        Returns:
            List[str]: Lista de identificadores de grupos
        """
        try:
            groups = list(self.redis_client.smembers(self.ALL_GROUPS_KEY))
            return sorted(groups)  # Retorna ordenado para consistência
            
        except redis.exceptions.RedisError as e:
            raise ConnectionError(f"Erro Redis ao listar grupos: {e}") from e
    
    def clear_all_data(self) -> bool:
        """
        Remove todos os dados de associações (útil para testes).
        
        ATENÇÃO: Esta operação é irreversível!
        
        Returns:
            bool: True se limpeza foi bem-sucedida
        """
        try:
            # Busca todas as chaves relacionadas
            user_keys = self.redis_client.keys(f"{self.USER_GROUPS_PREFIX}:*")
            group_keys = self.redis_client.keys(f"{self.GROUP_TOKENS_PREFIX}:*")
            
            # Remove todas as chaves em pipeline
            if user_keys or group_keys:
                pipe = self.redis_client.pipeline()
                for key in user_keys + group_keys:
                    pipe.delete(key)
                pipe.delete(self.ALL_GROUPS_KEY)
                pipe.execute()
            
            print("Todos os dados de associações foram removidos")
            return True
            
        except redis.exceptions.RedisError as e:
            raise ConnectionError(f"Erro Redis ao limpar dados: {e}") from e