"""
Classe base abstrata para todos os managers.

Define interface comum que todos os managers devem implementar.
Fornece métodos utilitários para notificação e logging.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from core.utils.logger import log


class BaseManager(ABC):
    """
    Classe abstrata base para todos os managers do sistema.
    
    Define contrato que cada manager deve seguir:
    - initialize(): Preparar recursos
    - cleanup(): Liberar recursos
    - _notify(): Notificar via callbacks do core
    
    Princípio: Single Responsibility
    - Cada manager tem responsabilidade bem definida
    - Apenas lógica de negócio (agnóstico de UI)
    
    Exemplo:
        class MyManager(BaseManager):
            def initialize(self) -> bool:
                # Preparar
                return True
            
            def cleanup(self) -> None:
                # Limpar
                pass
    """
    
    def __init__(self, core):
        """
        Inicializa o manager base.
        
        Args:
            core: Instância do SystemCore
        
        Nota: Subclasses devem chamar super().__init__(core)
        """
        self.core = core
        log.debug(f"✓ {self.__class__.__name__} criado")
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Inicializa o manager e prepara recursos.
        
        Deve ser implementado por subclasses.
        Chamado uma vez na startup.
        
        Returns:
            bool: True se inicializou com sucesso, False caso contrário
        
        Exemplo:
            def initialize(self) -> bool:
                try:
                    self.resources = self._load_resources()
                    return True
                except Exception as e:
                    log.error(f"Falha: {e}")
                    return False
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """
        Libera recursos do manager.
        
        Deve ser implementado por subclasses.
        Chamado na shutdown.
        
        Exemplo:
            def cleanup(self) -> None:
                if self.file:
                    self.file.close()
                if self.thread:
                    self.thread.stop()
        """
        pass
    
    def _notify(self, event: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Notifica via callbacks registrados no SystemCore.
        
        Permite que managers notifiquem listeners (UI, web, etc)
        sem acoplamento direto.
        
        Args:
            event: Nome do evento (ex: "capture_completed")
            data: Dict com dados do evento (opcional)
        
        Exemplo:
            self._notify("capture_completed", {"image": img_array})
        
        Nota: Se core não tiver _notify(), ignora silenciosamente
              (útil para testes)
        """
        if data is None:
            data = {}
        
        if hasattr(self.core, '_notify'):
            try:
                self.core._notify(event, data)
            except Exception as e:
                log.warning(f"Erro ao notificar evento '{event}': {e}")
    
    def _log(self, level: str, message: str) -> None:
        """
        Registra log com prefixo do manager.
        
        Args:
            level: Nível do log ("info", "warning", "error", "debug")
            message: Mensagem do log
        
        Exemplo:
            self._log("info", "Operação concluída")
            # Saída: [ManagerName] Operação concluída
        """
        manager_name = self.__class__.__name__
        prefixed_msg = f"[{manager_name}] {message}"
        
        if level == "info":
            log.info(prefixed_msg)
        elif level == "warning":
            log.warning(prefixed_msg)
        elif level == "error":
            log.error(prefixed_msg)
        elif level == "debug":
            log.debug(prefixed_msg)
    
    def __repr__(self) -> str:
        """Representação em string do manager"""
        return f"<{self.__class__.__name__}(core={self.core.__class__.__name__})>"
