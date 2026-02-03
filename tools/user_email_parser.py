import re
from typing import Tuple
from services.mongodb_group_resolver_service import MongoDBGroupResolverService

class UserEmailParser:
    @staticmethod
    def parse_email(email: str) -> Tuple[str, str]:
        """
        Recebe um email no formato 'usuario@empresa.com' e retorna uma tupla (usuario, empresa).
        Lança ValueError se o formato for inválido.
        """
        if not isinstance(email, str) or '@' not in email:
            raise ValueError("Formato de email inválido: '@' ausente.")
        usuario, dominio = email.split('@', 1)
        if not usuario or not dominio:
            raise ValueError("Formato de email inválido: usuário ou domínio ausente.")
        empresa = dominio.split('.', 1)[0]
        if not empresa:
            raise ValueError("Formato de email inválido: empresa não encontrada no domínio.")
        if not re.match(r'^[A-Za-z0-9_.+-]+$', usuario):
            raise ValueError("Formato de usuário inválido no email.")
        if not re.match(r'^[A-Za-z0-9_-]+$', empresa):
            raise ValueError("Formato de empresa inválido no email.")
        return usuario, empresa

    @staticmethod
    def parse_email_with_group(email: str, group_resolver: MongoDBGroupResolverService) -> Tuple[str, str, str]:
        """
        Recebe um email, obtém usuario e empresa via parse_email, consulta o grupo via group_resolver, retorna (usuario, empresa, grupo).
        """
        usuario, empresa = UserEmailParser.parse_email(email)
        grupo = group_resolver.get_group_for_user(usuario, empresa)
        return usuario, empresa, grupo
