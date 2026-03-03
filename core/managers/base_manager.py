from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from core.utils.logger import log

class BaseManager(ABC):

    def __init__(self, core):
        self.core = core
        log.debug(f'✓ {self.__class__.__name__} criado')

    @abstractmethod
    def initialize(self) -> bool:
        pass

    @abstractmethod
    def cleanup(self) -> None:
        pass

    def _notify(self, event: str, data: Optional[Dict[str, Any]]=None) -> None:
        if data is None:
            data = {}
        if hasattr(self.core, '_notify'):
            try:
                self.core._notify(event, data)
            except Exception as e:
                log.warning(f"Erro ao notificar evento '{event}': {e}")

    def _log(self, level: str, message: str) -> None:
        manager_name = self.__class__.__name__
        prefixed_msg = f'[{manager_name}] {message}'
        if level == 'info':
            log.info(prefixed_msg)
        elif level == 'warning':
            log.warning(prefixed_msg)
        elif level == 'error':
            log.error(prefixed_msg)
        elif level == 'debug':
            log.debug(prefixed_msg)

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}(core={self.core.__class__.__name__})>'