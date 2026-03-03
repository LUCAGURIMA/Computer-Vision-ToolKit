import cv2
import numpy as np
from typing import Dict, Any, Optional
from .icamera import ICamera
from core.utils.logger import log

class WebcamCamera(ICamera):

    def __init__(self, camera_index: int=0):
        self.camera_index = camera_index
        self._cap = None
        self._initialized = False
        log.info(f' Webcam criada (índice: {camera_index})')

    def initialize(self) -> bool:
        try:
            log.info(f'Abrindo webcam {self.camera_index}...')
            self._cap = cv2.VideoCapture(self.camera_index)
            if not self._cap.isOpened():
                log.error(f'Webcam {self.camera_index} não pôde ser aberta')
                return False
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            ret, test_frame = self._cap.read()
            if not ret:
                log.error('Webcam aberta mas não consegue capturar')
                self._cap.release()
                return False
            self._initialized = True
            log.info(f' Webcam {self.camera_index} inicializada')
            width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            log.info(f'  Resolução: {width}x{height}')
            return True
        except Exception as e:
            log.error(f' Erro ao inicializar webcam: {e}')
            return False

    def capture(self) -> Optional[np.ndarray]:
        if not self._initialized or self._cap is None:
            raise RuntimeError('Webcam não inicializada')
        try:
            ret, frame = self._cap.read()
            if ret and frame is not None:
                log.debug(f' Webcam capturou: {frame.shape}')
                return frame
            else:
                log.warning('Webcam não retornou frame')
                return None
        except Exception as e:
            log.error(f'Erro na captura da webcam: {e}')
            return None

    def release(self):
        if self._cap is not None:
            self._cap.release()
            log.info(' Webcam liberada')
        self._initialized = False

    def get_info(self) -> Dict[str, Any]:
        info = {'type': 'webcam', 'index': self.camera_index, 'initialized': self._initialized}
        if self._cap is not None:
            info['width'] = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            info['height'] = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            info['fps'] = self._cap.get(cv2.CAP_PROP_FPS)
        return info

    def is_available(self) -> bool:
        cap = cv2.VideoCapture(self.camera_index)
        if cap.isOpened():
            cap.release()
            return True
        return False

    def get_parameters(self) -> Dict[str, Any]:
        if not self._initialized or self._cap is None:
            return {}
        return {'brightness': {'value': self._cap.get(cv2.CAP_PROP_BRIGHTNESS), 'type': 'float', 'label': 'Brilho', 'min': -100, 'max': 100, 'step': 5, 'description': 'Ajusta brilho da imagem (-100 a 100)'}, 'contrast': {'value': self._cap.get(cv2.CAP_PROP_CONTRAST), 'type': 'float', 'label': 'Contraste', 'min': 0, 'max': 100, 'step': 5, 'description': 'Ajusta contraste da imagem (0 a 100)'}, 'saturation': {'value': self._cap.get(cv2.CAP_PROP_SATURATION), 'type': 'float', 'label': 'Saturação', 'min': 0, 'max': 100, 'step': 5, 'description': 'Ajusta saturação de cores (0 a 100)'}, 'hue': {'value': self._cap.get(cv2.CAP_PROP_HUE), 'type': 'float', 'label': 'Matiz', 'min': -180, 'max': 180, 'step': 10, 'description': 'Rotação de cor em graus'}, 'exposure': {'value': self._cap.get(cv2.CAP_PROP_EXPOSURE), 'type': 'float', 'label': 'Exposição', 'min': -13, 'max': 0, 'step': 1, 'description': 'Ajusta tempo de exposição (log scale, -13 a 0)'}, 'gain': {'value': self._cap.get(cv2.CAP_PROP_GAIN), 'type': 'float', 'label': 'Ganho', 'min': 0, 'max': 100, 'step': 5, 'description': 'Ganho do sensor (0 a 100)'}, 'width': {'value': int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)), 'type': 'int', 'label': 'Largura', 'min': 320, 'max': 3840, 'step': 160, 'description': 'Largura da imagem em pixels'}, 'height': {'value': int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)), 'type': 'int', 'label': 'Altura', 'min': 240, 'max': 2160, 'step': 120, 'description': 'Altura da imagem em pixels'}}

    def set_parameter(self, param_name: str, value: Any) -> bool:
        if not self._initialized or self._cap is None:
            return False
        try:
            param_map = {'brightness': cv2.CAP_PROP_BRIGHTNESS, 'contrast': cv2.CAP_PROP_CONTRAST, 'saturation': cv2.CAP_PROP_SATURATION, 'hue': cv2.CAP_PROP_HUE, 'exposure': cv2.CAP_PROP_EXPOSURE, 'gain': cv2.CAP_PROP_GAIN, 'width': cv2.CAP_PROP_FRAME_WIDTH, 'height': cv2.CAP_PROP_FRAME_HEIGHT}
            if param_name in param_map:
                self._cap.set(param_map[param_name], float(value))
                log.info(f' Webcam: {param_name} = {value}')
                return True
            return False
        except Exception as e:
            log.error(f'Erro ao ajustar webcam: {e}')
            return False
if __name__ == '__main__':
    print(' Testando webcam...')
    webcam = WebcamCamera(0)
    if webcam.initialize():
        print(f'Info: {webcam.get_info()}')
        frame = webcam.capture()
        if frame is not None:
            print(f'Frame shape: {frame.shape}')
        webcam.release()
    print(' Teste completo')