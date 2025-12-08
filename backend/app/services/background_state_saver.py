import asyncio
import logging
from backend.app.services.project_state_service import ProjectStateService
from backend.app.core.config import settings

class BackgroundStateSaver:
    _tasks = {}
    _interval_minutes = int(getattr(settings, 'PROJECT_STATE_SAVE_INTERVAL_MINUTES', 10))
    _logger = logging.getLogger("BackgroundStateSaver")

    @classmethod
    def schedule_periodic_save(cls, project_id: str, interval_minutes: int = None):
        if project_id in cls._tasks:
            return
        interval = interval_minutes or cls._interval_minutes
        loop = asyncio.get_event_loop()
        task = loop.create_task(cls._periodic_save(project_id, interval))
        cls._tasks[project_id] = task

    @classmethod
    async def _periodic_save(cls, project_id: str, interval_minutes: int):
        from backend.app.services.redis_session_service import RedisSessionService
        redis_service = RedisSessionService()
        last_saved_timestamp = None
        while True:
            try:
                session_data = redis_service.get_session_by_project_id(project_id)
                should_save = False
                if getattr(session_data, 'last_saved_to_blob', None) is None:
                    should_save = True
                else:
                    from datetime import datetime, timezone
                    try:
                        last_saved = session_data.last_saved_to_blob
                        if isinstance(last_saved, str):
                            last_saved_dt = datetime.fromisoformat(last_saved)
                        else:
                            last_saved_dt = last_saved
                        now = datetime.now(timezone.utc)
                        elapsed = (now - last_saved_dt).total_seconds() / 60.0
                        if elapsed >= interval_minutes:
                            should_save = True
                    except Exception as e:
                        cls._logger.warning(f"Erro ao calcular tempo desde o último salvamento do projeto {project_id}: {e}")
                        should_save = True
                if should_save:
                    url = await ProjectStateService.save_state_to_blob(session_data)
                    session_data.last_saved_to_blob = None
                    redis_service.update_session_status(project_id, 'saved')
                    cls._logger.info(f"Estado do projeto {project_id} salvo no Blob: {url}")
                else:
                    cls._logger.info(f"Estado do projeto {project_id} não foi salvo no Blob pois não houve alteração relevante.")
            except Exception as e:
                cls._logger.error(f"Erro ao salvar estado do projeto {project_id} no Blob: {e}")
            await asyncio.sleep(interval_minutes * 60)
