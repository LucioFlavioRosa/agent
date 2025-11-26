import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

try:
    from opencensus.ext.azure.log_exporter import AzureLogHandler
    AZURE_APP_INSIGHTS_AVAILABLE = True
except ImportError:
    AZURE_APP_INSIGHTS_AVAILABLE = False

class AzureLoggingService:
    def __init__(self, instrumentation_key: Optional[str] = None):
        self.logger = logging.getLogger("azure_mcp")
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(message)s')
        if AZURE_APP_INSIGHTS_AVAILABLE and instrumentation_key:
            handler = AzureLogHandler(connection_string=f'InstrumentationKey={instrumentation_key}')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        else:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            self.logger.addHandler(stream_handler)

    def log_job_event(self, job_id: str, analysis_type: str, event: str, details: Optional[Dict[str, Any]] = None, level: str = "info"):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "job_id": job_id,
            "analysis_type": analysis_type,
            "event": event,
            "details": details or {}
        }
        log_json = json.dumps(log_entry, ensure_ascii=False)
        if level == "info":
            self.logger.info(log_json)
        elif level == "warning":
            self.logger.warning(log_json)
        elif level == "error":
            self.logger.error(log_json)
        else:
            self.logger.debug(log_json)

    def log_exception(self, job_id: str, analysis_type: str, exception: Exception, details: Optional[Dict[str, Any]] = None):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "job_id": job_id,
            "analysis_type": analysis_type,
            "event": "exception",
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
            "details": details or {}
        }
        log_json = json.dumps(log_entry, ensure_ascii=False)
        self.logger.error(log_json)
