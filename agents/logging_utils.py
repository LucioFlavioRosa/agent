import logging
import os
from typing import Optional

_logger_instance = None

def init_logger() -> logging.Logger:
    global _logger_instance
    
    if _logger_instance is not None:
        return _logger_instance
    
    logger = logging.getLogger('agente_revisor_custom')
    logger.setLevel(logging.INFO)
    
    if logger.handlers:
        _logger_instance = logger
        return _logger_instance
    
    connection_string = os.getenv('APPLICATIONINSIGHTS_CONNECTION_STRING')
    
    if connection_string:
        try:
            from opencensus.ext.azure.log_exporter import AzureLogHandler
            azure_handler = AzureLogHandler(connection_string=connection_string)
            logger.addHandler(azure_handler)
            print("[Logging Utils] Azure Application Insights handler configurado com sucesso")
        except ImportError:
            print("[Logging Utils] AVISO: opencensus-ext-azure não disponível, usando logging local")
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            logger.addHandler(console_handler)
        except Exception as e:
            print(f"[Logging Utils] ERRO ao configurar Azure handler: {e}, usando logging local")
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            logger.addHandler(console_handler)
    else:
        print("[Logging Utils] AVISO: APPLICATIONINSIGHTS_CONNECTION_STRING não configurada, usando logging local")
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(console_handler)
    
    _logger_instance = logger
    return _logger_instance

def log_custom_data(**kwargs) -> None:
    try:
        logger = init_logger()
        
        custom_dimensions = {k: v for k, v in kwargs.items() if v is not None}
        
        if custom_dimensions:
            logger.info(
                "Execução do Agente Revisor",
                extra={'custom_dimensions': custom_dimensions}
            )
            print(f"[Logging Utils] Dados customizados enviados: {custom_dimensions}")
        else:
            print("[Logging Utils] AVISO: Nenhum dado customizado para enviar")
            
    except Exception as e:
        print(f"[Logging Utils] ERRO ao enviar dados customizados: {e}")