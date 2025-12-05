import asyncio
import logging
from backend.app.services.project_state_service import ProjectStateService
from backend.app.core.config import settings

class BackgroundStateSaver:
    _tasks = {}
    _interval_minutes = 60
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
        from backend.app.services.redis_session_service import RedisSessionService
        redis_service = RedisSessionService()
        while True:
            try:
                session_data = redis_service.get_session(session_id)
                url = await ProjectStateService.save_state_to_blob(session_data)
                session_data.last_saved_to_blob = None
                redis_service.update_session_status(session_id, 'saved')
                cls._logger.info(f"Estado da sessão {session_id} salvo no Blob: {url}")
            except Exception as e:
                cls._logger.error(f"Erro ao salvar estado da sessão {session_id} no Blob: {e}")
            await asyncio.sleep(interval_minutes * 60)
