from typing import Optional, Dict, Any
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap
import numpy as np
import cv2
from core.managers.capture_manager import CaptureManager
from core.utils.logger import log

class CaptureThread(QThread):
    image_captured = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, core):
        super().__init__()
        self.core = core
        self._should_capture = False

    def capture(self):
        self._should_capture = True
        self.start()

    def run(self):
        try:
            if not self._should_capture:
                return
            result = self.core.capture_image()
            if result:
                self.image_captured.emit(result)
            else:
                self.error_occurred.emit('Falha ao capturar imagem')
        except Exception as e:
            self.error_occurred.emit(f'Erro na captura: {str(e)}')
        finally:
            self._should_capture = False

class CaptureManagerQt(QObject):
    capture_started = pyqtSignal()
    image_captured = pyqtSignal(dict)
    capture_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    capture_finished = pyqtSignal()

    def __init__(self, core, camera_profiles=None):
        super().__init__()
        self.manager = CaptureManager(core, camera_profiles)
        core.register_callback('capture_completed', self._on_capture_completed)
        core.register_callback('capture_error', self._on_capture_error)
        self.capture_thread = CaptureThread(core)
        self.capture_thread.image_captured.connect(self._on_image_captured_raw)
        self.capture_thread.error_occurred.connect(self._on_capture_error)
        self.core = core
        self._log('info', 'Manager Qt criado')

    def _log(self, level: str, msg: str):
        try:
            logger_method = getattr(log, level, None)
            if callable(logger_method):
                logger_method(f'[CaptureManagerQt] {msg}')
            else:
                log.info(f'[CaptureManagerQt] {msg}')
        except Exception:
            log.info(f'[CaptureManagerQt] {msg}')

    def initialize(self) -> bool:
        return self.manager.initialize()

    def cleanup(self) -> None:
        if self.capture_thread.isRunning():
            self.capture_thread.wait()
        self.manager.cleanup()

    def set_crop_settings(self, enabled: bool, bbox: Optional[tuple]=None):
        self.manager.set_crop_settings(enabled, bbox)
        self._notify_crop_change()

    def reset_crop(self):
        self.manager.reset_crop()
        self._notify_crop_change()

    def set_inspect_after_capture(self, inspection_type: Optional[str]=None):
        self.manager.set_inspect_after_capture(inspection_type)

    def should_inspect_after_capture(self) -> Optional[str]:
        return self.manager.should_inspect_after_capture()

    def clear_images(self):
        self.manager.clear_images()

    def apply_profile(self, profile_name: str) -> bool:
        return self.manager.apply_profile(profile_name)

    def capture_image(self):
        self.capture_started.emit()
        self.capture_thread.capture()

    @pyqtSlot(dict)
    def _on_image_captured_raw(self, capture_result: Dict[str, Any]):
        try:
            result = self.manager.process_captured_image(capture_result)
            if result:
                self.image_captured.emit(result)
            else:
                self.error_occurred.emit('Falha ao processar imagem')
        except Exception as e:
            self._log('error', f'Erro ao processar: {e}')
            self.error_occurred.emit(str(e))
        finally:
            self.capture_finished.emit()

    def _on_capture_completed(self, data: Dict[str, Any]):
        self.capture_completed.emit(data)

    def _on_capture_error(self, data: Dict[str, Any]):
        error = data.get('error', 'Erro desconhecido')
        self.error_occurred.emit(error)

    def get_image_for_display(self) -> Optional[np.ndarray]:
        image = self.manager.get_current_image()
        if image is None:
            return None
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return rgb_image

    def get_image_info(self) -> Dict[str, Any]:
        return self.manager.get_image_info()

    def get_current_image(self) -> Optional[np.ndarray]:
        return self.manager.get_current_image()

    def get_raw_image(self) -> Optional[np.ndarray]:
        return self.manager.get_raw_image()

    def _notify_crop_change(self):
        info = self.get_image_info()
        self.capture_completed.emit({'crop_enabled': self.manager.crop_enabled, 'crop_bbox': self.manager.crop_bbox, 'info': info})

    def is_crop_enabled(self) -> bool:
        return self.manager.crop_enabled

    def get_crop_bbox(self) -> Optional[tuple]:
        return self.manager.crop_bbox

    @property
    def current_image(self) -> Optional[np.ndarray]:
        return self.manager.get_current_image()

    @property
    def raw_image(self) -> Optional[np.ndarray]:
        return self.manager.get_raw_image()