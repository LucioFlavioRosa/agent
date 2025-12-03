import asyncio
import logging
from backend.app.services.redis_session_service import RedisSessionService
from backend.app.services.project_state_service import ProjectStateService
from backend.app.core.config import settings

class BackgroundStateSaver:
    _tasks = {}
    _interval_minutes = int(getattr(settings, 'PROJECT_STATE_SAVE_INTERVAL_MINUTES', 10))
    _logger = logging.getLogger("BackgroundStateSaver")

    @classmethod
    def schedule_periodic_save(cls, session_id: str, interval_minutes: int = None):
        if session_id in cls._tasks:
            return
        interval = interval_minutes or cls._interval_minutes
        loop = asyncio.get_event_loop()
        task = loop.create_task(cls._periodic_save(session_id, interval))
        cls._tasks[session_id] = task

    @classmethod
    async def _periodic_save(cls, session_id: str, interval_minutes: int):
        redis_service = RedisSessionService()
        last_saved_timestamp = None
        while True:
            try:
                session_data = redis_service.get_session(session_id)
                last_modified = getattr(session_data, "last_modified", None)
                if last_modified:
                    if last_saved_timestamp != last_modified:
                        url = await ProjectStateService.save_state_to_blob(session_data)
                        session_data.last_saved_to_blob = None
                        redis_service.update_session_status(session_id, 'saved')
                        cls._logger.info(f"Estado da sessão {session_id} salvo no Blob: {url}")
                        last_saved_timestamp = last_modified
                    else:
                        cls._logger.info(f"Nenhuma alteração detectada na sessão {session_id}. Salvamento não necessário.")
                else:
                    url = await ProjectStateService.save_state_to_blob(session_data)
                    session_data.last_saved_to_blob = None
                    redis_service.update_session_status(session_id, 'saved')
                    cls._logger.info(f"Estado da sessão {session_id} salvo no Blob: {url}")
                    last_saved_timestamp = getattr(session_data, "last_modified", None)
            except Exception as e:
                cls._logger.error(f"Erro ao salvar estado da sessão {session_id} no Blob: {e}")
            await asyncio.sleep(interval_minutes * 60)
