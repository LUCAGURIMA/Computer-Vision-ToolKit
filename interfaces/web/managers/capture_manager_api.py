"""
CaptureManager API - Adapter REST para web.

Design: Adapter que expõe CaptureManager como endpoints REST.
"""

from typing import Optional, Dict, Any
import base64
import io
from datetime import datetime

import numpy as np
import cv2
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel, Field

from core.managers.capture_manager import CaptureManager
from core.utils.logger import log


# ========== Modelos Pydantic ==========

class CropSettingsRequest(BaseModel):
    """Request para configurar crop"""
    enabled: bool = Field(..., description="Habilita/desabilita crop")
    bbox: Optional[list] = Field(None, description="[x1, y1, x2, y2]")


class InspectionRequest(BaseModel):
    """Request para configurar inspeção"""
    type: Optional[str] = Field(None, description="segmentation, classification, ou null")


class ImageInfoResponse(BaseModel):
    """Response com informações da imagem"""
    shape: Optional[tuple] = Field(None, description="(H, W, C)")
    dtype: Optional[str] = None
    size_mb: float
    crop_applied: bool
    crop_bbox: Optional[list] = None
    status: str


class CaptureResponse(BaseModel):
    """Response padrão de captura"""
    success: bool
    message: str = ""
    data: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# ========== Adapter ==========

class CaptureManagerAPI:
    """
    API REST para CaptureManager agnóstico.
    
    Responsabilidade:
    - Converter requests HTTP em chamadas de manager
    - Serializar responses em JSON
    - Gerenciar conversão de formato (BGR↔RGB, etc)
    """
    
    def __init__(self, core, camera_profiles=None):
        """
        Inicializa o adapter.
        
        Args:
            core: SystemCore
            camera_profiles: CameraProfileManager (opcional)
        """
        self.manager = CaptureManager(core, camera_profiles)
        self.core = core
        self._log("info", "API Adapter criado")
    
    def _log(self, level: str, msg: str):
        """Log com prefixo"""
        log(f"[CaptureManagerAPI] {msg}", level)
    
    def initialize(self) -> bool:
        """Inicializa recursos"""
        return self.manager.initialize()
    
    def cleanup(self) -> None:
        """Limpa recursos"""
        self.manager.cleanup()
    
    # ========== Endpoints de captura ==========
    
    async def capture_image(self) -> CaptureResponse:
        """
        Captura imagem via câmera.
        
        Returns:
            CaptureResponse com:
            - success: bool
            - data: {
                "shape": tuple,
                "crop_applied": bool,
                "size_mb": float,
                "image_b64": str (base64)
              }
        """
        try:
            # Captura via SystemCore
            result = self.core.capture_image()
            if not result:
                return CaptureResponse(
                    success=False,
                    message="Falha ao capturar imagem"
                )
            
            # Processa com manager
            processed = self.manager.process_captured_image(result)
            if not processed:
                return CaptureResponse(
                    success=False,
                    message="Falha ao processar imagem"
                )
            
            image = processed.get("image")
            if image is None:
                return CaptureResponse(
                    success=False,
                    message="Nenhuma imagem após processamento"
                )
            
            # Serializa imagem em base64 (RGB para web)
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            _, buffer = cv2.imencode('.png', rgb_image)
            image_b64 = base64.b64encode(buffer).decode('utf-8')
            
            return CaptureResponse(
                success=True,
                message="Captura realizada com sucesso",
                data={
                    "shape": processed.get("shape"),
                    "crop_applied": processed.get("crop_applied", False),
                    "size_mb": image.nbytes / (1024 * 1024),
                    "image_b64": image_b64,
                    "timestamp": processed.get("timestamp", "")
                }
            )
        
        except Exception as e:
            self._log("error", f"Erro ao capturar: {e}")
            return CaptureResponse(
                success=False,
                message=f"Erro: {str(e)}"
            )
    
    # ========== Endpoints de crop ==========
    
    def set_crop_settings(self, request: CropSettingsRequest) -> CaptureResponse:
        """
        Define configurações de crop.
        
        Args:
            request: CropSettingsRequest
        
        Returns:
            CaptureResponse
        
        Exemplo:
            POST /capture/crop
            {
                "enabled": true,
                "bbox": [100, 100, 500, 500]
            }
        """
        try:
            bbox = tuple(request.bbox) if request.bbox else None
            self.manager.set_crop_settings(request.enabled, bbox)
            
            return CaptureResponse(
                success=True,
                message=f"Crop {'habilitado' if request.enabled else 'desabilitado'}",
                data={
                    "crop_enabled": request.enabled,
                    "crop_bbox": request.bbox
                }
            )
        
        except Exception as e:
            self._log("error", f"Erro ao configurar crop: {e}")
            return CaptureResponse(
                success=False,
                message=f"Erro: {str(e)}"
            )
    
    def reset_crop(self) -> CaptureResponse:
        """
        Remove configuração de crop.
        
        Returns:
            CaptureResponse
        """
        try:
            self.manager.reset_crop()
            return CaptureResponse(
                success=True,
                message="Crop removido",
                data={"crop_enabled": False}
            )
        
        except Exception as e:
            self._log("error", f"Erro ao resetar crop: {e}")
            return CaptureResponse(
                success=False,
                message=f"Erro: {str(e)}"
            )
    
    # ========== Endpoints de inspeção ==========
    
    def set_inspection(self, request: InspectionRequest) -> CaptureResponse:
        """
        Define inspeção automática após captura.
        
        Args:
            request: InspectionRequest
        
        Returns:
            CaptureResponse
        
        Exemplo:
            POST /capture/inspection
            {
                "type": "segmentation"
            }
        """
        try:
            self.manager.set_inspect_after_capture(request.type)
            
            return CaptureResponse(
                success=True,
                message=f"Inspeção {'habilitada' if request.type else 'desabilitada'}",
                data={
                    "inspection_type": request.type
                }
            )
        
        except Exception as e:
            self._log("error", f"Erro ao configurar inspeção: {e}")
            return CaptureResponse(
                success=False,
                message=f"Erro: {str(e)}"
            )
    
    def get_inspection_status(self) -> CaptureResponse:
        """
        Retorna status de inspeção automática.
        
        Returns:
            CaptureResponse com inspection_type
        """
        try:
            insp_type = self.manager.should_inspect_after_capture()
            return CaptureResponse(
                success=True,
                data={
                    "inspection_type": insp_type,
                    "enabled": insp_type is not None
                }
            )
        
        except Exception as e:
            self._log("error", f"Erro ao consultar inspeção: {e}")
            return CaptureResponse(
                success=False,
                message=f"Erro: {str(e)}"
            )
    
    # ========== Endpoints de informação ==========
    
    def get_image_info(self) -> CaptureResponse:
        """
        Retorna informações sobre imagem atual.
        
        Returns:
            CaptureResponse com ImageInfoResponse
        """
        try:
            info = self.manager.get_image_info()
            
            return CaptureResponse(
                success=True,
                data={
                    "shape": info.get("shape"),
                    "dtype": info.get("dtype"),
                    "size_mb": info.get("size_mb", 0),
                    "crop_applied": info.get("crop_applied", False),
                    "crop_bbox": info.get("crop_bbox"),
                    "status": info.get("status", "OK")
                }
            )
        
        except Exception as e:
            self._log("error", f"Erro ao consultar info: {e}")
            return CaptureResponse(
                success=False,
                message=f"Erro: {str(e)}"
            )
    
    def get_status(self) -> CaptureResponse:
        """
        Retorna status completo do manager.
        
        Returns:
            CaptureResponse com informações consolidadas
        """
        try:
            info = self.manager.get_image_info()
            insp_type = self.manager.should_inspect_after_capture()
            
            return CaptureResponse(
                success=True,
                data={
                    "image": info,
                    "crop": {
                        "enabled": self.manager.crop_enabled,
                        "bbox": self.manager.crop_bbox
                    },
                    "inspection": {
                        "type": insp_type,
                        "enabled": insp_type is not None
                    }
                }
            )
        
        except Exception as e:
            self._log("error", f"Erro ao consultar status: {e}")
            return CaptureResponse(
                success=False,
                message=f"Erro: {str(e)}"
            )
    
    # ========== Endpoints de limpeza ==========
    
    def clear_images(self) -> CaptureResponse:
        """
        Limpa imagens armazenadas.
        
        Returns:
            CaptureResponse
        """
        try:
            self.manager.clear_images()
            return CaptureResponse(
                success=True,
                message="Imagens limpas"
            )
        
        except Exception as e:
            self._log("error", f"Erro ao limpar imagens: {e}")
            return CaptureResponse(
                success=False,
                message=f"Erro: {str(e)}"
            )
    
    # ========== Endpoints de perfil ==========
    
    def apply_profile(self, profile_name: str) -> CaptureResponse:
        """
        Aplica perfil de câmera.
        
        Args:
            profile_name: Nome do perfil
        
        Returns:
            CaptureResponse
        """
        try:
            success = self.manager.apply_profile(profile_name)
            
            if success:
                return CaptureResponse(
                    success=True,
                    message=f"Perfil '{profile_name}' aplicado",
                    data={"profile": profile_name}
                )
            else:
                return CaptureResponse(
                    success=False,
                    message=f"Falha ao aplicar perfil '{profile_name}'"
                )
        
        except Exception as e:
            self._log("error", f"Erro ao aplicar perfil: {e}")
            return CaptureResponse(
                success=False,
                message=f"Erro: {str(e)}"
            )
