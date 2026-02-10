"""
Gerenciador de câmeras com fallback automático.

Esta é a CLASSE MAIS IMPORTANTE do sistema de câmeras.
Ela gerencia múltiplas câmeras e tenta automaticamente a próxima se uma falhar.
"""

from typing import List, Optional, Dict, Any
import numpy as np

from .icamera import ICamera
from .basler_camera import BaslerCamera
from .webcam_camera import WebcamCamera
from .mock_camera import MockCamera

from core.utils.logger import log
from config import CAMERA_CONFIG

class CameraManager:
    """
    Gerencia múltiplas câmeras com estratégia de fallback.
    
    Funciona como uma "corrente" de câmeras:
    1. Tenta a câmera principal (Basler)
    2. Se falhar, tenta a primeira fallback (Webcam)
    3. Se falhar, tenta a segunda fallback (Mock)
    4. Se todas falharem, levanta erro
    
    Isso garante que o sistema SEMPRE tenha uma câmera disponível.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            config (Dict): Configuração das câmeras
        """
        self.config = config or CAMERA_CONFIG
        self.cameras: List[ICamera] = []
        self.active_camera: Optional[ICamera] = None
        self._current_index = -1
        
        log.info("📡 Inicializando CameraManager...")
        self._create_camera_chain()
    
    def _create_camera_chain(self):
        """Cria a cadeia de câmeras baseada na configuração"""
        
        # 1. Câmera principal (Basler) - se existir
        if "primary" in self.config:
            primary_config = self.config["primary"]
            if primary_config["type"] == "basler":
                camera = BaslerCamera(ip_address=primary_config.get("ip"))
                self.cameras.append(camera)
                log.info(f"➕ Adicionada câmera principal: Basler")
        
        # 2. Câmeras de fallback
        for i, fb_config in enumerate(self.config.get("fallbacks", [])):
            camera_type = fb_config["type"]
            
            if camera_type == "webcam":
                camera = WebcamCamera(camera_index=fb_config.get("index", 0))
                self.cameras.append(camera)
                log.info(f"➕ Adicionada fallback {i+1}: Webcam")
            
            elif camera_type == "mock":
                camera = MockCamera(image_path=fb_config.get("image_path"))
                self.cameras.append(camera)
                log.info(f"➕ Adicionada fallback {i+1}: MockCamera")
        
        log.info(f"📊 Total de câmeras na cadeia: {len(self.cameras)}")
    
    def initialize(self) -> bool:
        """
        Tenta inicializar as câmeras na ordem até conseguir.
        
        Returns:
            bool: True se alguma câmera inicializou
        """
        max_retries = self.config.get("primary", {}).get("max_retries", 3)
        
        for i, camera in enumerate(self.cameras):
            log.info(f"🔄 Tentando inicializar câmera {i+1}/{len(self.cameras)}: {camera.__class__.__name__}")
            
            # Tenta várias vezes (útil para Basler que pode falhar no início)
            for attempt in range(max_retries):
                try:
                    log.debug(f"  Tentativa {attempt + 1}/{max_retries}...")
                    
                    if camera.initialize():
                        self.active_camera = camera
                        self._current_index = i
                        
                        info = camera.get_info()
                        log.info(f"✅ Câmera ativa: {camera.__class__.__name__}")
                        log.info(f"   Tipo: {info.get('type', 'N/A')}")
                        if 'model' in info:
                            log.info(f"   Modelo: {info['model']}")
                        if 'width' in info and 'height' in info:
                            log.info(f"   Resolução: {info['width']}x{info['height']}")
                        
                        return True
                    
                except Exception as e:
                    log.warning(f"  Tentativa {attempt + 1} falhou: {e}")
                    
                    if attempt < max_retries - 1:
                        log.debug("  Aguardando 1 segundo antes de tentar novamente...")
                        import time
                        time.sleep(1)
                    else:
                        log.error(f"❌ Todas as tentativas falharam para {camera.__class__.__name__}")
            
            # Se chegou aqui, esta câmera falhou
            log.warning(f"⚠️  {camera.__class__.__name__} não pôde ser inicializada")
        
        # Se nenhuma câmera funcionou
        log.error("❌ TODAS as câmeras falharam!")
        return False
    
    def capture(self) -> Optional[np.ndarray]:
        """
        Captura uma imagem usando a câmera ativa.
        
        Se a câmera ativa falhar, tenta a próxima automaticamente.
        
        Returns:
            Optional[np.ndarray]: Imagem ou None se todas falharem
        """
        if self.active_camera is None:
            raise RuntimeError("Nenhuma câmera inicializada. Chame initialize() primeiro.")
        
        # Tenta com a câmera atual
        try:
            image = self.active_camera.capture()
            if image is not None:
                return image
            else:
                log.warning("Câmera ativa retornou None, tentando fallback...")
                raise RuntimeError("Captura falhou")
                
        except Exception as e:
            log.warning(f"❌ Câmera ativa falhou: {e}")
            return self._try_next_camera()
    
    def _try_next_camera(self) -> Optional[np.ndarray]:
        """
        Tenta a próxima câmera na cadeia.
        
        Returns:
            Optional[np.ndarray]: Imagem da próxima câmera ou None
        """
        if self._current_index + 1 >= len(self.cameras):
            log.error("⛔ Nenhuma câmera restante na cadeia!")
            return None
        
        # Libera câmera atual
        if self.active_camera:
            self.active_camera.release()
        
        # Avança para próxima câmera
        self._current_index += 1
        self.active_camera = self.cameras[self._current_index]
        
        log.info(f"🔄 Alternando para câmera {self._current_index + 1}/{len(self.cameras)}: "
                f"{self.active_camera.__class__.__name__}")
        
        # Tenta inicializar
        try:
            if self.active_camera.initialize():
                return self.active_camera.capture()
            else:
                return self._try_next_camera()  # Recursão para próxima
        except Exception as e:
            log.error(f"Falha ao alternar câmera: {e}")
            return self._try_next_camera()
    
    def get_active_camera_info(self) -> Dict[str, Any]:
        """Informações da câmera ativa"""
        if self.active_camera:
            info = self.active_camera.get_info()
            info["index"] = self._current_index
            info["total_cameras"] = len(self.cameras)
            return info
        return {"status": "no_active_camera"}
    
    def get_all_cameras_info(self) -> List[Dict[str, Any]]:
        """Informações de todas as câmeras com status de conexão"""
        infos = []
        for i, camera in enumerate(self.cameras):
            info = camera.get_info()
            info["position"] = i
            info["is_active"] = (i == self._current_index)
            # Tenta verificar se a câmera está realmente conectada
            info["connected"] = camera._initialized if hasattr(camera, '_initialized') else False
            infos.append(info)
        return infos
    
    def detect_all_cameras(self) -> List[Dict[str, Any]]:
        """
        Detecta status de TODAS as câmeras (não em cascata).
        
        Testa cada câmera individualmente para determinar:
        - Se está disponível (conectável)
        - Suas propriedades (resolução, modelo, etc)
        
        Returns:
            List[Dict]: Informações de cada câmera com status de conexão
        """
        infos = []
        
        for i, camera in enumerate(self.cameras):
            camera_info = {
                "position": i,
                "type": camera.__class__.__name__.replace("Camera", "").lower(),
                "is_active": (i == self._current_index),
                "connected": False,
                "available": False
            }
            
            try:
                # Se câmera é mock, sempre está disponível
                if camera.__class__.__name__ == "MockCamera":
                    camera_info["available"] = True
                    camera_info["connected"] = hasattr(camera, '_initialized') and camera._initialized
                    if camera_info["connected"]:
                        camera_info.update(camera.get_info())
                    else:
                        camera_info.update({
                            "model": "Mock (Simulada)",
                            "width": 640,
                            "height": 480
                        })
                else:
                    # Para câmeras reais, tenta detectar
                    if hasattr(camera, '_initialized') and camera._initialized:
                        # Já está inicializada
                        camera_info["connected"] = True
                        camera_info["available"] = True
                        camera_info.update(camera.get_info())
                    else:
                        # Tenta testar disponibilidade sem inicializar
                        # (cada câmera pode ter sua própria lógica)
                        if hasattr(camera, 'test_connection'):
                            if camera.test_connection():
                                camera_info["available"] = True
                        else:
                            # Fallback: assume disponível para webcam
                            if camera.__class__.__name__ == "WebcamCamera":
                                camera_info["available"] = True
                        
                        # Se foi detectada, tenta pegar info básica
                        if camera_info["available"]:
                            try:
                                camera_info.update(camera.get_info())
                            except:
                                pass
            
            except Exception as e:
                log.debug(f"Erro ao detectar câmera {i}: {e}")
                camera_info["available"] = False
            
            infos.append(camera_info)
        
        return infos
    
    def release(self):
        """Libera todas as câmeras"""
        for camera in self.cameras:
            try:
                camera.release()
            except:
                pass
        
        self.active_camera = None
        self._current_index = -1
        log.info("🔒 Todas as câmeras liberadas")

# Teste do CameraManager
if __name__ == "__main__":
    print("\n" + "="*50)
    print("🧪 TESTE DO CAMERA MANAGER")
    print("="*50)
    
    # Cria manager
    manager = CameraManager()
    
    # Inicializa (deve tentar Basler, depois Webcam, depois Mock)
    if manager.initialize():
        print("\n✅ CameraManager inicializado com sucesso!")
        
        # Mostra informações
        active_info = manager.get_active_camera_info()
        print(f"\n📊 Câmera ativa:")
        for key, value in active_info.items():
            print(f"  {key}: {value}")
        
        # Tenta capturar
        print("\n📸 Tentando capturar imagem...")
        image = manager.capture()
        
        if image is not None:
            print(f"✅ Imagem capturada: {image.shape}")
            
            # Se for MockCamera, salva imagem para ver
            if active_info.get("type") == "mock":
                import cv2
                cv2.imwrite("teste_mock_camera.jpg", image)
                print("💾 Imagem mock salva como 'teste_mock_camera.jpg'")
        else:
            print("❌ Falha ao capturar imagem")
        
        # Libera recursos
        manager.release()
    
    else:
        print("❌ CameraManager não pôde ser inicializado")
    
    print("\n" + "="*50)
    print("✅ TESTE COMPLETO")
    print("="*50)