"""Thread for performing inspection operations."""

from typing import TYPE_CHECKING, Optional
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from core.utils.logger import log

if TYPE_CHECKING:
    from core.system_core import SystemCore


class InspectionThread(QThread):
    """Thread for performing inspection (segmentation or classification).
    
    Signals:
        inspection_completed: Emitted when inspection finishes with results
        error_occurred: Emitted when an error occurs during inspection
    """
    
    inspection_completed = pyqtSignal(dict, str)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        core: 'SystemCore',
        inspection_type: str,
        image: Optional[np.ndarray] = None,
        model_name: Optional[str] = None
    ):
        """Initialize inspection thread.
        
        Args:
            core: SystemCore instance for model execution
            inspection_type: Type of inspection ('segmentation' or 'classification')
            image: Image to inspect (optional)
            model_name: Name of model to use (optional)
        """
        super().__init__()
        self.core = core
        self.inspection_type = inspection_type
        self.image = image
        self.model_name = model_name
        self._logger_name = self.__class__.__name__

    def run(self):
        """Execute inspection operation in thread."""
        try:
            if self.inspection_type == 'segmentation':
                result = self.core.perform_segmentation(
                    self.image,
                    model_name=self.model_name
                )
            elif self.inspection_type == 'classification':
                result = self.core.perform_classification(
                    self.image,
                    model_name=self.model_name
                )
            else:
                raise ValueError(
                    f'Invalid inspection type: {self.inspection_type}'
                )
            self.inspection_completed.emit(result, self.inspection_type)
        except Exception as e:
            log.error(
                f'[{self._logger_name}] Exception during inspection: {e}',
                exc_info=True
            )
            self.error_occurred.emit(repr(e))
