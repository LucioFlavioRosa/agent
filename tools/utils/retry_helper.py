import time
import logging

def retry_with_backoff(func, max_attempts=3, initial_delay=1, backoff_factor=2, exceptions=(Exception,), job_id=None, context_msg=None):
    delay = initial_delay
    last_exception = None
    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except exceptions as e:
            last_exception = e
            msg = f"[RETRY_HELPER] Tentativa {attempt}/{max_attempts} falhou."
            if job_id:
                msg = f"[{job_id}] " + msg
            if context_msg:
                msg += f" Contexto: {context_msg}."
            msg += f" Erro: {str(e)}"
            logging.warning(msg)
            if attempt == max_attempts:
                break
            time.sleep(delay)
            delay *= backoff_factor
    raise last_exception
