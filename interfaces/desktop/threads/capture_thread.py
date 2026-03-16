"""Base capture thread for single image capture operations."""

from typing import TYPE_CHECKING
from PyQt5.QtCore import QThread, pyqtSignal
from core.utils.logger import log

if TYPE_CHECKING:
    from core.system_core import SystemCore


class CaptureThread(QThread):
    """Thread for performing single image captures.
    
    Signals:
        image_captured: Emitted when image is successfully captured
        error_occurred: Emitted when an error occurs during capture
    """
    
    image_captured = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, core: 'SystemCore'):
        """Initialize capture thread.
        
        Args:
            core: SystemCore instance for image capture
        """
        super().__init__()
        self.core = core
        self._logger_name = self.__class__.__name__

    def run(self):
        """Execute capture operation in thread."""
        try:
            result = self.core.capture_image()
            if result and result.get('success'):
                self.image_captured.emit(result)
            else:
                self.error_occurred.emit('Falha na captura')
        except Exception as e:
            log.error(f'[{self._logger_name}] Exception during capture: {e}', exc_info=True)
            self.error_occurred.emit(str(e))
