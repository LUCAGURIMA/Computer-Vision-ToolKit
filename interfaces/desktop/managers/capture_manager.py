"""
CaptureManager - Gerencia captura e processamento de imagens
Responsabilidade: Separar lógica de captura da UI
"""

from typing import Optional, Dict, Any
import numpy as np
import cv2
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot


class CaptureManager(QObject):
    """
    Gerencia todo o fluxo de captura de imagens.
    
    Signals:
        - image_captured: Emitido quando imagem é capturada (dict com 'image', 'camera_info', 'timestamp')
        - error_occurred: Emitido quando erro na captura (str com mensagem de erro)
        - capture_started: Emitido quando captura inicia
        - capture_finished: Emitido quando captura termina
    """
    
    # Signals
    image_captured = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    capture_started = pyqtSignal()
    capture_finished = pyqtSignal()
    
    def __init__(self, core):
        """
        Inicializa o gerenciador de captura.
        
        Args:
            core: SystemCore instance com métodos de câmera
        """
        super().__init__()
        self.core = core
        
        # Estado da captura
        self.current_image: Optional[np.ndarray] = None
        self.raw_image: Optional[np.ndarray] = None
        
        # Configurações de crop
        self.crop_enabled: bool = False
        self.crop_bbox: Optional[tuple] = None  # (x, y, w, h)
        
        # Flag para inspeção após captura
        self._inspect_after_capture: Optional[str] = None
    
    def set_crop_settings(self, enabled: bool, bbox: Optional[tuple] = None):
        """
        Define configurações de crop para próximas capturas.
        
        Args:
            enabled: Se crop está habilitado
            bbox: Bounding box (x, y, width, height) ou None
        """
        self.crop_enabled = enabled
        self.crop_bbox = bbox
    
    def reset_crop(self):
        """Desabilita crop"""
        self.crop_enabled = False
        self.crop_bbox = None
    
    def set_inspect_after_capture(self, inspection_type: Optional[str] = None):
        """
        Define se deve iniciar inspeção após captura.
        
        Args:
            inspection_type: "segmentation", "classification" ou None para desabilitar
        """
        self._inspect_after_capture = inspection_type
    
    def get_current_image(self) -> Optional[np.ndarray]:
        """Retorna imagem processada atual"""
        return self.current_image
    
    def get_raw_image(self) -> Optional[np.ndarray]:
        """Retorna imagem raw (sem processamento)"""
        return self.raw_image
    
    def process_captured_image(self, capture_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa imagem capturada (aplica crop se necessário).
        
        Args:
            capture_result: Dict com resultado da captura (image, camera_info, timestamp, etc)
                           Emitido pelo CaptureThread como signal
        
        Returns:
            Dict com 'image' processada e metadados
        """
        try:
            # Extrai dados do resultado
            raw_image = capture_result.get("image")
            camera_info = capture_result.get("camera_info", {})
            timestamp = capture_result.get("timestamp", "")
            
            if raw_image is None:
                raise Exception("Nenhuma imagem no resultado de captura")
            
            self.raw_image = raw_image
            
            # Aplica crop se habilitado
            processed_image = raw_image
            if self.crop_enabled and self.crop_bbox:
                try:
                    ops = [{"name": "crop", "bbox": self.crop_bbox}]
                    processed_image = self.core.preprocess_image(raw_image, ops)
                except Exception as e:
                    raise Exception(f"Falha ao aplicar crop: {e}")
            
            self.current_image = processed_image
            
            return {
                "image": processed_image,
                "raw_image": raw_image,
                "camera_info": camera_info,
                "timestamp": timestamp,
                "shape": processed_image.shape,
            }
        
        except Exception as e:
            self.error_occurred.emit(str(e))
            return None
    
    def get_image_for_display(self, image: Optional[np.ndarray] = None) -> Optional[np.ndarray]:
        """
        Prepara imagem para display em Qt (converte BGR→RGB).
        
        Args:
            image: Imagem numpy (padrão: current_image)
        
        Returns:
            Imagem em RGB para display ou None
        """
        if image is None:
            image = self.current_image
        
        if image is None:
            return None
        
        # Converte BGR (OpenCV) para RGB se necessário
        if len(image.shape) == 3 and image.shape[2] == 3:
            try:
                return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            except:
                return image
        
        return image
    
    def get_image_info(self) -> str:
        """Retorna string com informações sobre imagem atual"""
        if self.current_image is None:
            return "Nenhuma imagem capturada"
        
        shape = self.current_image.shape
        dtype = self.current_image.dtype
        size_mb = self.current_image.nbytes / (1024 * 1024)
        
        return f"Shape: {shape} | Dtype: {dtype} | Size: {size_mb:.2f}MB"
    
    def clear_images(self):
        """Limpa imagens armazenadas"""
        self.current_image = None
        self.raw_image = None
        self._inspect_after_capture = None
    
    def should_inspect_after_capture(self) -> Optional[str]:
        """Retorna tipo de inspeção a fazer após captura (ou None)"""
        return self._inspect_after_capture
