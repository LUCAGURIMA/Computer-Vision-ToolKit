"""
CaptureManager com suporte a PyQt5 - Threading e signals para desktop.

Design: Thin wrapper que adiciona threading e signals ao CaptureManager agnóstico.
"""

from typing import Optional, Dict, Any
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap
import numpy as np
import cv2

from core.managers.capture_manager import CaptureManager
from core.utils.logger import log


class CaptureThread(QThread):
    """Thread para captura não-bloqueante"""
    
    image_captured = pyqtSignal(dict)  # Emite resultado da captura
    error_occurred = pyqtSignal(str)   # Emite erro
    
    def __init__(self, core):
        super().__init__()
        self.core = core
        self._should_capture = False
    
    def capture(self):
        """Inicia captura"""
        self._should_capture = True
        self.start()
    
    def run(self):
        """Executa captura em thread separada"""
        try:
            if not self._should_capture:
                return
            
            # Captura imagem via SystemCore
            result = self.core.capture_image()
            if result:
                self.image_captured.emit(result)
            else:
                self.error_occurred.emit("Falha ao capturar imagem")
        
        except Exception as e:
            self.error_occurred.emit(f"Erro na captura: {str(e)}")
        
        finally:
            self._should_capture = False


class CaptureManagerQt(QObject):
    """
    Gerenciador de captura com suporte a PyQt5.
    
    Adiciona:
    - Threading não-bloqueante
    - Signals PyQt5 para UI updates
    - Conversão BGR→RGB para Qt display
    - Integração com CaptureManager agnóstico
    """
    
    # Signals
    capture_started = pyqtSignal()
    image_captured = pyqtSignal(dict)       # Emite resultado processado
    capture_completed = pyqtSignal(dict)    # Emite info da captura
    error_occurred = pyqtSignal(str)
    capture_finished = pyqtSignal()
    
    def __init__(self, core, camera_profiles=None):
        """
        Inicializa o gerenciador.
        
        Args:
            core: SystemCore
            camera_profiles: CameraProfileManager (opcional)
        """
        super().__init__()
        
        # Instância agnóstica
        self.manager = CaptureManager(core, camera_profiles)
        
        # Registra callbacks do manager agnóstico
        core.register_callback("capture_completed", self._on_capture_completed)
        core.register_callback("capture_error", self._on_capture_error)
        
        # Thread de captura
        self.capture_thread = CaptureThread(core)
        self.capture_thread.image_captured.connect(self._on_image_captured_raw)
        self.capture_thread.error_occurred.connect(self._on_capture_error)
        
        self.core = core
        
        self._log("info", "Manager Qt criado")
    
    def _log(self, level: str, msg: str):
        """Log com prefixo"""
        log(f"[CaptureManagerQt] {msg}", level)
    
    # ========== Delegação para manager agnóstico ==========
    
    def initialize(self) -> bool:
        """Inicializa recursos"""
        return self.manager.initialize()
    
    def cleanup(self) -> None:
        """Limpa recursos"""
        if self.capture_thread.isRunning():
            self.capture_thread.wait()
        self.manager.cleanup()
    
    def set_crop_settings(self, enabled: bool, bbox: Optional[tuple] = None):
        """Define configurações de crop"""
        self.manager.set_crop_settings(enabled, bbox)
        self._notify_crop_change()
    
    def reset_crop(self):
        """Desabilita crop"""
        self.manager.reset_crop()
        self._notify_crop_change()
    
    def set_inspect_after_capture(self, inspection_type: Optional[str] = None):
        """Define inspeção após captura"""
        self.manager.set_inspect_after_capture(inspection_type)
    
    def should_inspect_after_capture(self) -> Optional[str]:
        """Retorna tipo de inspeção"""
        return self.manager.should_inspect_after_capture()
    
    def clear_images(self):
        """Limpa imagens armazenadas"""
        self.manager.clear_images()
    
    def apply_profile(self, profile_name: str) -> bool:
        """Aplica perfil de câmera"""
        return self.manager.apply_profile(profile_name)
    
    # ========== Métodos específicos de captura ==========
    
    def capture_image(self):
        """
        Inicia captura de forma não-bloqueante.
        
        Emite signals:
        - capture_started: Quando captura inicia
        - image_captured: Quando imagem é processada
        - error_occurred: Se houver erro
        - capture_finished: Quando captura termina
        """
        self.capture_started.emit()
        self.capture_thread.capture()
    
    @pyqtSlot(dict)
    def _on_image_captured_raw(self, capture_result: Dict[str, Any]):
        """
        Processa imagem raw capturada.
        
        Chamado por capture_thread quando imagem é capturada.
        """
        try:
            # Processa com manager agnóstico
            result = self.manager.process_captured_image(capture_result)
            
            if result:
                self.image_captured.emit(result)
            else:
                self.error_occurred.emit("Falha ao processar imagem")
        
        except Exception as e:
            self._log("error", f"Erro ao processar: {e}")
            self.error_occurred.emit(str(e))
        
        finally:
            self.capture_finished.emit()
    
    def _on_capture_completed(self, data: Dict[str, Any]):
        """Callback do manager agnóstico - captura completada"""
        self.capture_completed.emit(data)
    
    def _on_capture_error(self, data: Dict[str, Any]):
        """Callback do manager agnóstico - erro na captura"""
        error = data.get("error", "Erro desconhecido")
        self.error_occurred.emit(error)
    
    # ========== Métodos de display (específicos de Qt) ==========
    
    def get_image_for_display(self) -> Optional[np.ndarray]:
        """
        Retorna imagem convertida para RGB (para Qt display).
        
        Conversão: BGR (OpenCV) → RGB (Qt)
        
        Returns:
            np.ndarray RGB ou None
        """
        image = self.manager.get_current_image()
        if image is None:
            return None
        
        # OpenCV usa BGR, Qt usa RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return rgb_image
    
    def get_image_info(self) -> Dict[str, Any]:
        """
        Retorna informações sobre a imagem.
        
        Returns:
            Dict com shape, dtype, size_mb, crop_applied, status
        """
        return self.manager.get_image_info()
    
    def get_current_image(self) -> Optional[np.ndarray]:
        """Retorna imagem processada (BGR)"""
        return self.manager.get_current_image()
    
    def get_raw_image(self) -> Optional[np.ndarray]:
        """Retorna imagem raw (BGR)"""
        return self.manager.get_raw_image()
    
    def _notify_crop_change(self):
        """Notifica UI sobre mudança de crop"""
        info = self.get_image_info()
        self.capture_completed.emit({
            "crop_enabled": self.manager.crop_enabled,
            "crop_bbox": self.manager.crop_bbox,
            "info": info
        })
    
    # ========== Getters para estado ==========
    
    def is_crop_enabled(self) -> bool:
        """Retorna se crop está habilitado"""
        return self.manager.crop_enabled
    
    def get_crop_bbox(self) -> Optional[tuple]:
        """Retorna bounding box do crop"""
        return self.manager.crop_bbox
    
    @property
    def current_image(self) -> Optional[np.ndarray]:
        """Property para acesso à imagem processada"""
        return self.manager.get_current_image()
    
    @property
    def raw_image(self) -> Optional[np.ndarray]:
        """Property para acesso à imagem raw"""
        return self.manager.get_raw_image()
