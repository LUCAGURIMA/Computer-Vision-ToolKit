"""
Câmera Mock (falsa) para desenvolvimento e fallback.

Útil para:
1. Testar sem câmera real
2. Desenvolver em computador sem câmera
3. Fallback quando todas as câmeras falham
"""

import cv2
import numpy as np
from typing import Dict, Any, Optional
from pathlib import Path

from .icamera import ICamera
from core.utils.logger import log
from config import ASSETS_DIR

class MockCamera(ICamera):
    """
    Câmera fake que lê imagens do disco.
    
    Simula uma câmera real para desenvolvimento e teste.
    """
    
    def __init__(self, image_path: Optional[str] = None):
        """
        Args:
            image_path (str): Caminho para imagem de teste.
                             Se None, usa imagem padrão.
        """
        self.image_path = image_path or str(ASSETS_DIR / "test_image.jpg")
        self._image = None
        self._initialized = False
        
        log.info(f"🎭 MockCamera criada (imagem: {self.image_path})")
    
    def initialize(self) -> bool:
        """
        Carrega a imagem do disco.
        
        Returns:
            bool: True se imagem existe e carregou
        """
        try:
            path = Path(self.image_path)
            
            if not path.exists():
                # Se não existe, cria uma imagem fake
                log.warning(f"Imagem não encontrada: {self.image_path}")
                log.info("Criando imagem fake para teste...")
                
                # Cria uma imagem colorida fake
                self._image = np.zeros((480, 640, 3), dtype=np.uint8)
                
                # Adiciona algum conteúdo
                cv2.putText(self._image, "MOCK CAMERA", (50, 240),
                           cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 3)
                cv2.putText(self._image, "Sistema em Desenvolvimento", (30, 300),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                log.info("✅ Imagem fake criada")
            else:
                # Carrega imagem real
                self._image = cv2.imread(str(path))
                if self._image is None:
                    raise ValueError(f"Não foi possível ler imagem: {path}")
                
                log.info(f"✅ Imagem carregada: {self._image.shape}")
            
            self._initialized = True
            return True
            
        except Exception as e:
            log.error(f"❌ Erro ao inicializar MockCamera: {e}")
            return False
    
    def capture(self) -> Optional[np.ndarray]:
        """
        Retorna a imagem carregada.
        
        Simula uma captura real.
        """
        if not self._initialized:
            raise RuntimeError("MockCamera não inicializada")
        
        log.debug("📸 MockCamera: retornando imagem simulada")
        return self._image.copy()  # Retorna cópia para não modificar original
    
    def release(self):
        """Libera recursos (não faz nada em mock)"""
        self._image = None
        self._initialized = False
        log.debug("🔒 MockCamera liberada")
    
    def get_info(self) -> Dict[str, Any]:
        """Informações da câmera mock"""
        info = {
            "type": "mock",
            "image_path": self.image_path,
            "initialized": self._initialized,
            "note": "Câmera simulada para desenvolvimento"
        }
        
        if self._image is not None:
            info["image_shape"] = self._image.shape
            info["image_dtype"] = str(self._image.dtype)
        
        return info
    
    def is_available(self) -> bool:
        """MockCamera está sempre disponível"""
        return True

# Teste rápido
if __name__ == "__main__":
    print("🧪 Testando MockCamera...")
    
    # Cria diretório assets se não existir
    ASSETS_DIR.mkdir(exist_ok=True)
    
    mock = MockCamera()
    if mock.initialize():
        print(f"Info: {mock.get_info()}")
        
        frame = mock.capture()
        if frame is not None:
            print(f"Frame shape: {frame.shape}")
        
        mock.release()
    
    print("✅ Teste completo")