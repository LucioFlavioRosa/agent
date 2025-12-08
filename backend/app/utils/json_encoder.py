import json
from datetime import datetime, date
from typing import Any

def _default_json_encoder(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return str(obj)

def safe_json_dumps(data: Any, ensure_ascii: bool = False, separators=(",", ":")) -> str:
    return json.dumps(data, default=_default_json_encoder, ensure_ascii=ensure_ascii, separators=separators)
