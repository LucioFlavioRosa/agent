import logging
from typing import Any, List, Optional

class BaseService:
    """
    Classe base para serviços, fornecendo métodos comuns para validação de parâmetros,
    tratamento de erros e registro de operações. Facilita manutenção e reutilização.
    """
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def _validate_required_params(self, params: dict, required_keys: List[str]) -> None:
        """
        Valida se todas as chaves obrigatórias estão presentes no dicionário de parâmetros.
        Não realiza validação manual de tipos ou valores, apenas existência das chaves.
        """
        missing = [key for key in required_keys if key not in params]
        if missing:
            raise ValueError(f"Parâmetros obrigatórios ausentes: {', '.join(missing)}")

    def _handle_error(self, error: Exception, context: Optional[str] = None) -> None:
        """
        Tratamento centralizado de erros. Apenas registra o erro, mantendo o fluxo padrão.
        """
        msg = f"Erro: {str(error)}"
        if context:
            msg = f"[{context}] {msg}"
        self.logger.error(msg)
        # Não faz validação manual, apenas loga o erro

    def _log_operation(self, message: str, level: str = "info") -> None:
        """
        Registra operações e mensagens relevantes para manutenção.
        """
        if level == "debug":
            self.logger.debug(message)
        elif level == "warning":
            self.logger.warning(message)
        elif level == "error":
            self.logger.error(message)
        else:
            self.logger.info(message)
