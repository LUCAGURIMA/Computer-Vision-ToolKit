from typing import Optional, Dict, Any
import numpy as np
import cv2
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

class CaptureManager(QObject):
    image_captured = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    capture_started = pyqtSignal()
    capture_finished = pyqtSignal()

    def __init__(self, core):
        super().__init__()
        self.core = core
        self.current_image: Optional[np.ndarray] = None
        self.raw_image: Optional[np.ndarray] = None
        self.crop_enabled: bool = False
        self.crop_bbox: Optional[tuple] = None
        self._inspect_after_capture: Optional[str] = None

    def set_crop_settings(self, enabled: bool, bbox: Optional[tuple]=None):
        self.crop_enabled = enabled
        self.crop_bbox = bbox

    def reset_crop(self):
        self.crop_enabled = False
        self.crop_bbox = None

    def set_inspect_after_capture(self, inspection_type: Optional[str]=None):
        self._inspect_after_capture = inspection_type

    def get_current_image(self) -> Optional[np.ndarray]:
        return self.current_image

    def get_raw_image(self) -> Optional[np.ndarray]:
        return self.raw_image

    def process_captured_image(self, capture_result: Dict[str, Any]) -> Dict[str, Any]:
        try:
            raw_image = capture_result.get('image')
            camera_info = capture_result.get('camera_info', {})
            timestamp = capture_result.get('timestamp', '')
            if raw_image is None:
                raise Exception('Nenhuma imagem no resultado de captura')
            self.raw_image = raw_image
            processed_image = raw_image
            if self.crop_enabled and self.crop_bbox:
                try:
                    ops = [{'name': 'crop', 'bbox': self.crop_bbox}]
                    processed_image = self.core.preprocess_image(raw_image, ops)
                except Exception as e:
                    raise Exception(f'Falha ao aplicar crop: {e}')
            self.current_image = processed_image
            return {'image': processed_image, 'raw_image': raw_image, 'camera_info': camera_info, 'timestamp': timestamp, 'shape': processed_image.shape}
        except Exception as e:
            self.error_occurred.emit(str(e))
            return None

    def get_image_for_display(self, image: Optional[np.ndarray]=None) -> Optional[np.ndarray]:
        if image is None:
            image = self.current_image
        if image is None:
            return None
        if len(image.shape) == 3 and image.shape[2] == 3:
            try:
                return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            except:
                return image
        return image

    def get_image_info(self) -> str:
        if self.current_image is None:
            return 'Nenhuma imagem capturada'
        shape = self.current_image.shape
        dtype = self.current_image.dtype
        size_mb = self.current_image.nbytes / (1024 * 1024)
        return f'Shape: {shape} | Dtype: {dtype} | Size: {size_mb:.2f}MB'

    def clear_images(self):
        self.current_image = None
        self.raw_image = None
        self._inspect_after_capture = None

    def should_inspect_after_capture(self) -> Optional[str]:
        return self._inspect_after_capture