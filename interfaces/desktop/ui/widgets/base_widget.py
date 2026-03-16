"""UI widgets for desktop interface tabs and components."""

from PyQt5.QtWidgets import QWidget
from core.utils.logger import log


class BaseWidget(QWidget):
    """Base class for all UI widgets.
    
    Provides common functionality and interface for all widgets.
    """

    def __init__(self, parent=None):
        """Initialize base widget.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._logger_name = self.__class__.__name__

    def _log(self, level: str, message: str):
        """Log a message with widget context.
        
        Args:
            level: Log level string ('debug', 'info', 'warning', 'error')
            message: Message to log
        """
        try:
            logger_method = getattr(log, level, None)
            if callable(logger_method):
                logger_method(f'[{self._logger_name}] {message}')
            else:
                log.info(f'[{self._logger_name}] {message}')
        except Exception as e:
            log.error(f'Logging error: {e}')

    def initialize(self) -> bool:
        """Initialize widget resources.
        
        Returns:
            True if initialization successful, False otherwise
        """
        return True

    def cleanup(self):
        """Clean up widget resources."""
        pass
