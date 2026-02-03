import re
from typing import Tuple

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
