"""
CaptureManager - Gerencia captura e processamento de imagens (agnóstico de UI).

Responsabilidade: Lógica pura de captura, sem dependência de PyQt5.

Design: Reutilizável em desktop (PyQt5), web (FastAPI), CLI, etc.
"""

from typing import Optional, Dict, Any
import numpy as np

from .base_manager import BaseManager
from core.utils.logger import log


class CaptureManager(BaseManager):
    """
    Gerencia todo o fluxo de captura de imagens (agnóstico de UI).
    
    Funcionalidades:
    - Processar imagens capturadas
    - Aplicar crop se configurado
    - Armazenar imagens processadas e raw
    - Retornar informações sobre imagens
    
    Não contém: Threading, Qt signals, HTTP endpoints, etc.
    """
    
    def __init__(self, core, camera_profiles: Optional[Any] = None):
        """
        Inicializa o gerenciador de captura.
        
        Args:
            core: SystemCore instance com métodos de câmera
            camera_profiles: CameraProfileManager (opcional)
        """
        super().__init__(core)
        self.camera_profiles = camera_profiles
        
        # Estado da captura
        self.current_image: Optional[np.ndarray] = None
        self.raw_image: Optional[np.ndarray] = None
        
        # Configurações de crop
        self.crop_enabled: bool = False
        self.crop_bbox: Optional[tuple] = None  # [x1, y1, x2, y2]
        
        # Flag para inspeção após captura
        self._inspect_after_capture: Optional[str] = None
        
        self._log("info", "Manager criado")
    
    def initialize(self) -> bool:
        """Inicializa o manager"""
        try:
            if self.camera_profiles:
                return self.camera_profiles.load_profiles()
            return True
        except Exception as e:
            self._log("error", f"Falha na inicialização: {e}")
            return False
    
    def cleanup(self) -> None:
        """Limpa recursos"""
        self.clear_images()
        self._log("info", "Limpeza completa")
    
    def set_crop_settings(self, enabled: bool, bbox: Optional[tuple] = None):
        """
        Define configurações de crop para próximas capturas.
        
        Args:
            enabled: Se crop está habilitado
            bbox: Bounding box [x1, y1, x2, y2] ou None
        
        Exemplo:
            manager.set_crop_settings(True, [100, 100, 500, 500])
        """
        self.crop_enabled = enabled
        self.crop_bbox = bbox
        if enabled:
            self._log("info", f"Crop habilitado: {bbox}")
        else:
            self._log("info", "Crop desabilitado")
    
    def reset_crop(self):
        """Desabilita crop"""
        self.crop_enabled = False
        self.crop_bbox = None
        self._log("info", "Crop resetado")
    
    def set_inspect_after_capture(self, inspection_type: Optional[str] = None):
        """
        Define se deve iniciar inspeção após captura.
        
        Args:
            inspection_type: "segmentation", "classification" ou None para desabilitar
        
        Exemplo:
            manager.set_inspect_after_capture("segmentation")
        """
        self._inspect_after_capture = inspection_type
        if inspection_type:
            self._log("debug", f"Inspeção após captura: {inspection_type}")
    
    def process_captured_image(self, capture_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Processa imagem capturada (aplica crop se necessário).
        
        Args:
            capture_result: Dict com resultado da captura
                {
                    "image": np.ndarray (BGR),
                    "camera_info": dict,
                    "timestamp": str,
                    ...
                }
        
        Returns:
            Dict com 'image' processada e metadados, ou None se erro
            {
                "image": np.ndarray (processada),
                "raw_image": np.ndarray,
                "camera_info": dict,
                "timestamp": str,
                "shape": tuple,
                "crop_applied": bool
            }
        
        Exemplo:
            result = manager.process_captured_image(capture_result)
            if result:
                print(f"Imagem shape: {result['shape']}")
        """
        try:
            # Extrai dados do resultado
            raw_image = capture_result.get("image")
            camera_info = capture_result.get("camera_info", {})
            timestamp = capture_result.get("timestamp", "")
            
            if raw_image is None:
                raise Exception("Nenhuma imagem no resultado de captura")
            
            self.raw_image = raw_image
            crop_applied = False
            
            # Aplica crop se habilitado
            processed_image = raw_image
            if self.crop_enabled and self.crop_bbox:
                try:
                    ops = [{"name": "crop", "bbox": self.crop_bbox}]
                    processed_image = self.core.preprocess_image(raw_image, ops)
                    crop_applied = True
                    self._log("debug", f"Crop aplicado: {self.crop_bbox}")
                except Exception as e:
                    self._log("error", f"Falha ao aplicar crop: {e}")
                    raise Exception(f"Falha ao aplicar crop: {e}")
            
            self.current_image = processed_image
            
            result = {
                "image": processed_image,
                "raw_image": raw_image,
                "camera_info": camera_info,
                "timestamp": timestamp,
                "shape": processed_image.shape,
                "crop_applied": crop_applied,
            }
            
            self._notify("capture_completed", {
                "shape": processed_image.shape,
                "crop_applied": crop_applied
            })
            self._log("info", f"Imagem processada: {processed_image.shape}")
            
            return result
        
        except Exception as e:
            self._log("error", f"Erro ao processar imagem: {e}")
            self._notify("capture_error", {"error": str(e)})
            return None
    
    def get_current_image(self) -> Optional[np.ndarray]:
        """
        Retorna imagem processada atual.
        
        Returns:
            np.ndarray (processada com crop se aplicável) ou None
        """
        return self.current_image
    
    def get_raw_image(self) -> Optional[np.ndarray]:
        """
        Retorna imagem raw (sem processamento).
        
        Returns:
            np.ndarray (original da câmera) ou None
        """
        return self.raw_image
    
    def get_image_info(self) -> Dict[str, Any]:
        """
        Retorna informações sobre imagem atual.
        
        Returns:
            Dict com:
            - shape: Dimensões (H, W, C)
            - dtype: Tipo de dados
            - size_mb: Tamanho em MB
            - crop_applied: Se crop foi aplicado
        
        Exemplo:
            info = manager.get_image_info()
            print(f"Shape: {info['shape']}, Size: {info['size_mb']:.2f}MB")
        """
        if self.current_image is None:
            return {
                "shape": None,
                "dtype": None,
                "size_mb": 0,
                "crop_applied": False,
                "status": "Nenhuma imagem"
            }
        
        shape = self.current_image.shape
        dtype = str(self.current_image.dtype)
        size_mb = self.current_image.nbytes / (1024 * 1024)
        
        return {
            "shape": shape,
            "dtype": dtype,
            "size_mb": size_mb,
            "crop_applied": self.crop_enabled,
            "crop_bbox": self.crop_bbox if self.crop_enabled else None,
            "status": "OK"
        }
    
    def clear_images(self):
        """Limpa imagens armazenadas"""
        self.current_image = None
        self.raw_image = None
        self._inspect_after_capture = None
        self._log("debug", "Imagens limpas")
    
    def should_inspect_after_capture(self) -> Optional[str]:
        """
        Retorna tipo de inspeção a fazer após captura.
        
        Returns:
            "segmentation", "classification" ou None
        
        Exemplo:
            insp_type = manager.should_inspect_after_capture()
            if insp_type:
                perform_inspection(insp_type)
        """
        return self._inspect_after_capture
    
    def apply_profile(self, profile_name: str) -> bool:
        """
        Aplica um perfil de câmera.
        
        Args:
            profile_name: Nome do perfil
        
        Returns:
            bool: True se sucesso
        
        Exemplo:
            success = manager.apply_profile("profile_1")
        """
        if not self.camera_profiles:
            self._log("warning", "Nenhum camera_profiles disponível")
            return False
        
        try:
            profile = self.camera_profiles.get_profile(profile_name)
            if not profile:
                self._log("error", f"Perfil não encontrado: {profile_name}")
                return False
            
            # Aplicar configurações do perfil
            # (exemplo: resolution, exposure, etc)
            self._log("info", f"Perfil aplicado: {profile_name}")
            return True
        except Exception as e:
            self._log("error", f"Erro ao aplicar perfil: {e}")
            return False
