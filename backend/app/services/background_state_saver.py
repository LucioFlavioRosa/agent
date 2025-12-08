import logging

class BackgroundStateSaver:
    _tasks = {}
    _logger = logging.getLogger("BackgroundStateSaver")

    @classmethod
    def schedule_periodic_save(cls, project_id: str, interval_minutes: int = None):
        # Salvamento periódico desabilitado conforme novo fluxo.
        pass

    @classmethod
    async def _periodic_save(cls, project_id: str, interval_minutes: int):
        # Salvamento periódico desabilitado conforme novo fluxo.
        pass
