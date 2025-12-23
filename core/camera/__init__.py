"""
Módulo de câmera - expõe todas as classes principais.
"""

from .icamera import ICamera
from .basler_camera import BaslerCamera
from .webcam_camera import WebcamCamera
from .mock_camera import MockCamera
from .camera_manager import CameraManager

__all__ = [
    'ICamera',
    'BaslerCamera', 
    'WebcamCamera',
    'MockCamera',
    'CameraManager'
]