"""
Implementação da câmera Webcam como fallback.

Esta é uma alternativa quando a Basler não está disponível.
"""

import cv2
import numpy as np
from typing import Dict, Any, Optional

from .icamera import ICamera
from core.utils.logger import log

class WebcamCamera(ICamera):
    """
    Implementação de câmera webcam comum.
    
    Uso como fallback quando a Basler falha.
    """
    
    def __init__(self, camera_index: int = 0):
        """
        Args:
            camera_index (int): Índice da webcam (geralmente 0 para a primeira)
        """
        self.camera_index = camera_index
        self._cap = None  # Objeto VideoCapture do OpenCV
        self._initialized = False
        
        log.info(f"📹 Webcam criada (índice: {camera_index})")
    
    def initialize(self) -> bool:
        """
        Inicializa a webcam.
        
        Returns:
            bool: True se conseguiu abrir a webcam
        """
        try:
            log.info(f"Abrindo webcam {self.camera_index}...")
            
            # Tenta abrir a webcam
            self._cap = cv2.VideoCapture(self.camera_index)
            
            if not self._cap.isOpened():
                log.error(f"Webcam {self.camera_index} não pôde ser aberta")
                return False
            
            # Tenta configurar resolução
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            
            # Lê uma frame para testar
            ret, test_frame = self._cap.read()
            if not ret:
                log.error("Webcam aberta mas não consegue capturar")
                self._cap.release()
                return False
            
            self._initialized = True
            log.info(f"✅ Webcam {self.camera_index} inicializada")
            
            # Log da resolução real
            width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            log.info(f"  Resolução: {width}x{height}")
            
            return True
            
        except Exception as e:
            log.error(f"❌ Erro ao inicializar webcam: {e}")
            return False
    
    def capture(self) -> Optional[np.ndarray]:
        """
        Captura uma imagem da webcam.
        
        Returns:
            Optional[np.ndarray]: Imagem ou None se falhar
        """
        if not self._initialized or self._cap is None:
            raise RuntimeError("Webcam não inicializada")
        
        try:
            # Lê um frame
            ret, frame = self._cap.read()
            
            if ret and frame is not None:
                log.debug(f"✅ Webcam capturou: {frame.shape}")
                return frame
            else:
                log.warning("Webcam não retornou frame")
                return None
                
        except Exception as e:
            log.error(f"Erro na captura da webcam: {e}")
            return None
    
    def release(self):
        """Libera a webcam"""
        if self._cap is not None:
            self._cap.release()
            log.info("🔒 Webcam liberada")
        self._initialized = False
    
    def get_info(self) -> Dict[str, Any]:
        """Informações da webcam"""
        info = {
            "type": "webcam",
            "index": self.camera_index,
            "initialized": self._initialized
        }
        
        if self._cap is not None:
            info["width"] = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            info["height"] = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            info["fps"] = self._cap.get(cv2.CAP_PROP_FPS)
        
        return info
    
    def is_available(self) -> bool:
        """Webcam geralmente está disponível (mas pode estar em uso)"""
        # Testa rapidamente se consegue abrir
        cap = cv2.VideoCapture(self.camera_index)
        if cap.isOpened():
            cap.release()
            return True
        return False

# Teste rápido
if __name__ == "__main__":
    print("🧪 Testando webcam...")
    webcam = WebcamCamera(0)
    
    if webcam.initialize():
        print(f"Info: {webcam.get_info()}")
        
        # Tenta capturar (mas não mostra)
        frame = webcam.capture()
        if frame is not None:
            print(f"Frame shape: {frame.shape}")
        
        webcam.release()
    
    print("✅ Teste completo")