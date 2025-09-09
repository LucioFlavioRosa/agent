import logging
import os
from typing import Optional, Dict, Any

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

def log_custom_data(
    job_id: Optional[str] = None,
    projeto: Optional[str] = None,
    tokens_in: Optional[int] = None,
    tokens_out: Optional[int] = None,
    status: Optional[str] = None,
    **kwargs
) -> None:
    try:
        logger = init_logger()
        
        custom_dimensions = {}
        
        if job_id is not None:
            custom_dimensions['job_id'] = job_id
        if projeto is not None:
            custom_dimensions['projeto'] = projeto
        if tokens_in is not None:
            custom_dimensions['tokens_in'] = tokens_in
        if tokens_out is not None:
            custom_dimensions['tokens_out'] = tokens_out
        if status is not None:
            custom_dimensions['status'] = status
        
        for key, value in kwargs.items():
            if value is not None:
                custom_dimensions[key] = value
        
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