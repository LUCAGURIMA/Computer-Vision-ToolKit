"""
Implementação da câmera Basler (a que você já usa).

Esta classe IMPLEMENTA a interface ICamera.
Isso significa que ela PROMETE ter todos os métodos que ICamera exige.
"""

import cv2
import numpy as np
from typing import Dict, Any, Optional
import sys

# Importa nossa interface
from .icamera import ICamera

# Tenta importar pypylon (pode não estar instalado)
try:
    from pypylon import pylon
    BASLER_AVAILABLE = True
except ImportError:
    BASLER_AVAILABLE = False
    print("⚠️  Pypylon não instalado. Câmera Basler não disponível.")

# Importa nosso logger
from core.utils.logger import log

class BaslerCamera(ICamera):
    """
    Implementação concreta para câmera Basler.
    
    Herda de ICamera, então DEVE implementar todos os métodos abstratos.
    """
    
    def __init__(self, ip_address: Optional[str] = None):
        """
        Inicializa a câmera Basler.
        
        Args:
            ip_address (str, optional): IP específico da câmera. 
                                       Se None, usa a primeira disponível.
        """
        self.ip_address = ip_address
        self._camera = None  # Instância da câmera Basler
        self._initialized = False
        
        log.info(f"📷 Câmera Basler criada (IP: {ip_address or 'auto'})")
    
    def initialize(self) -> bool:
        """
        Inicializa a conexão com a câmera Basler.
        
        Returns:
            bool: True se inicializou com sucesso
            
        Raises:
            RuntimeError: Se não encontrar câmera ou pypylon não instalado
        """
        if not BASLER_AVAILABLE:
            raise RuntimeError("Biblioteca pypylon não disponível. Instale com: pip install pypylon")
        
        try:
            log.info("Inicializando câmera Basler...")
            
            # Pega fábrica de dispositivos
            tl_factory = pylon.TlFactory.GetInstance()
            
            # Lista dispositivos disponíveis
            devices = tl_factory.EnumerateDevices()
            
            if not devices:
                raise RuntimeError("Nenhuma câmera Basler encontrada.")
            
            # Log das câmeras encontradas
            for i, device in enumerate(devices):
                model = device.GetModelName() if hasattr(device, "GetModelName") else "Desconhecido"
                ip = device.GetIpAddress() if hasattr(device, "GetIpAddress") else "N/A"
                log.info(f"  Câmera {i}: {model} (IP: {ip})")
            
            # Seleciona dispositivo
            selected_device = None
            
            # Se IP específico foi fornecido, tenta encontrar
            if self.ip_address:
                for device in devices:
                    if hasattr(device, "GetIpAddress") and device.GetIpAddress() == self.ip_address:
                        selected_device = device
                        log.info(f"Usando câmera com IP: {self.ip_address}")
                        break
            
            # Se não encontrou pelo IP, usa a primeira
            if selected_device is None:
                selected_device = devices[0]
                model = selected_device.GetModelName() if hasattr(selected_device, "GetModelName") else "Desconhecido"
                log.info(f"Usando primeira câmera disponível: {model}")
            
            # Cria e abre a câmera
            self._camera = pylon.InstantCamera(tl_factory.CreateDevice(selected_device))
            self._camera.Open()
            
            # Configura para resolução máxima
            self._camera.Width.SetValue(self._camera.Width.Max)
            self._camera.Height.SetValue(self._camera.Height.Max)
            
            # Configura exposição automática (ajuste conforme necessidade)
            try:
                self._camera.ExposureAuto.SetValue("Continuous")
                log.info("Exposição automática ativada")
            except:
                log.warning("Não foi possível configurar exposição automática")
            
            self._initialized = True
            log.info("✅ Câmera Basler inicializada com sucesso")
            return True
            
        except Exception as e:
            log.error(f"❌ Falha ao inicializar câmera Basler: {e}")
            self._initialized = False
            return False
    
    def capture(self) -> Optional[np.ndarray]:
        """
        Captura uma imagem da câmera Basler.
        
        Returns:
            Optional[np.ndarray]: Imagem em formato BGR (OpenCV)
            
        Raises:
            RuntimeError: Se câmera não está inicializada
        """
        if not self._initialized or self._camera is None:
            raise RuntimeError("Câmera não inicializada. Chame initialize() primeiro.")
        
        try:
            log.debug("Capturando imagem da Basler...")
            
            # Captura uma única imagem
            self._camera.StartGrabbingMax(1)
            grab_result = self._camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            
            if grab_result.GrabSucceeded():
                # Pega o array da imagem
                image = grab_result.Array
                
                # Se for imagem Bayer (preto e branco), converte para BGR
                if len(image.shape) == 2:
                    image = cv2.cvtColor(image, cv2.COLOR_BAYER_BG2BGR)
                
                grab_result.Release()
                
                log.debug(f"✅ Imagem capturada: {image.shape}")
                return image
            else:
                grab_result.Release()
                raise RuntimeError("Falha na captura da imagem")
                
        except Exception as e:
            log.error(f"❌ Erro ao capturar imagem: {e}")
            return None
    
    def release(self):
        """Libera recursos da câmera"""
        if self._camera is not None and self._camera.IsOpen():
            self._camera.Close()
            log.info("🔒 Câmera Basler liberada")
        self._initialized = False
    
    def get_info(self) -> Dict[str, Any]:
        """Retorna informações da câmera"""
        info = {
            "type": "basler",
            "ip": self.ip_address,
            "initialized": self._initialized,
            "available": BASLER_AVAILABLE
        }
        
        if self._camera and self._camera.IsOpen():
            info["model"] = self._camera.GetDeviceInfo().GetModelName()
            info["width"] = self._camera.Width.GetValue()
            info["height"] = self._camera.Height.GetValue()
        
        return info
    
    def is_available(self) -> bool:
        """Verifica se a câmera Basler está disponível"""
        return BASLER_AVAILABLE
    
    def get_parameters(self) -> Dict[str, Any]:
        """Retorna parâmetros específicos da câmera Basler"""
        if not self._initialized or not self._camera or not self._camera.IsOpen():
            return {}
        
        try:
            return {
                "gain": {
                    "value": float(self._camera.Gain.GetValue()) if hasattr(self._camera, 'Gain') else 0,
                    "type": "float",
                    "label": "Ganho",
                    "min": 0,
                    "max": 30,
                    "step": 0.5,
                    "description": "Ganho da câmera (0 a 30 dB)"
                },
                "exposure_time": {
                    "value": float(self._camera.ExposureTime.GetValue()) if hasattr(self._camera, 'ExposureTime') else 0,
                    "type": "float",
                    "label": "Tempo de Exposição (µs)",
                    "min": 26,
                    "max": 30000000,
                    "step": 1000,
                    "description": "Tempo de exposição em microsegundos (26 µs a 30s)"
                },
                "frame_rate": {
                    "value": float(self._camera.AcquisitionFrameRate.GetValue()) if hasattr(self._camera, 'AcquisitionFrameRate') else 30,
                    "type": "float",
                    "label": "Taxa de Quadros (FPS)",
                    "min": 1,
                    "max": 200,
                    "step": 1,
                    "description": "Taxa de aquisição em quadros por segundo"
                },
                "width": {
                    "value": int(self._camera.Width.GetValue()),
                    "type": "int",
                    "label": "Largura",
                    "min": 100,
                    "max": 2048,
                    "step": 4,
                    "description": "Largura da imagem em pixels"
                },
                "height": {
                    "value": int(self._camera.Height.GetValue()),
                    "type": "int",
                    "label": "Altura",
                    "min": 100,
                    "max": 2048,
                    "step": 4,
                    "description": "Altura da imagem em pixels"
                },
                "balance_white": {
                    "value": "auto" if hasattr(self._camera, 'BalanceWhiteAuto') and self._camera.BalanceWhiteAuto.GetValue() == 1 else "manual",
                    "type": "enum",
                    "label": "Balanço de Branco",
                    "options": ["manual", "auto"],
                    "description": "Modo de balanço de branco"
                }
            }
        except Exception as e:
            log.debug(f"Erro ao ler parâmetros Basler: {e}")
            return {}
    
    def set_parameter(self, param_name: str, value: Any) -> bool:
        """Define parâmetro da câmera Basler"""
        if not self._initialized or not self._camera or not self._camera.IsOpen():
            return False
        
        try:
            if param_name == "gain" and hasattr(self._camera, 'Gain'):
                self._camera.Gain.SetValue(float(value))
                log.info(f"📷 Basler: Ganho = {value} dB")
                return True
            
            elif param_name == "exposure_time" and hasattr(self._camera, 'ExposureTime'):
                self._camera.ExposureTime.SetValue(int(value))
                log.info(f"📷 Basler: Tempo de exposição = {value} µs")
                return True
            
            elif param_name == "frame_rate" and hasattr(self._camera, 'AcquisitionFrameRate'):
                self._camera.AcquisitionFrameRate.SetValue(float(value))
                log.info(f"📷 Basler: Taxa de quadros = {value} FPS")
                return True
            
            elif param_name == "width" and hasattr(self._camera, 'Width'):
                self._camera.Width.SetValue(int(value))
                log.info(f"📷 Basler: Largura = {value} px")
                return True
            
            elif param_name == "height" and hasattr(self._camera, 'Height'):
                self._camera.Height.SetValue(int(value))
                log.info(f"📷 Basler: Altura = {value} px")
                return True
            
            elif param_name == "balance_white" and hasattr(self._camera, 'BalanceWhiteAuto'):
                mode_val = 1 if str(value).lower() == "auto" else 0
                self._camera.BalanceWhiteAuto.SetValue(mode_val)
                log.info(f"📷 Basler: Balanço de branco = {value}")
                return True
            
            return False
        except Exception as e:
            log.error(f"Erro ao ajustar Basler: {e}")
            return False

# Teste da implementação
if __name__ == "__main__":
    # Teste básico da câmera
    print("🧪 Testando câmera Basler...")
    
    camera = BaslerCamera()
    print(f"Disponível: {camera.is_available()}")
    
    if camera.is_available():
        try:
            if camera.initialize():
                print(f"Info: {camera.get_info()}")
                # Não capturamos imagem no teste para não travar sem câmera
                camera.release()
        except Exception as e:
            print(f"Erro: {e}")
    
    print("✅ Teste completo")