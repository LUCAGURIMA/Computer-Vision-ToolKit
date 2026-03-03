from .icamera import ICamera
try:
    from .basler_camera import BaslerCamera
except Exception as e:
    print(f'⚠️  Aviso: BaslerCamera não pode ser importado: {e}')
    BaslerCamera = None
from .webcam_camera import WebcamCamera
from .mock_camera import MockCamera
from .camera_manager import CameraManager
__all__ = ['ICamera', 'BaslerCamera', 'WebcamCamera', 'MockCamera', 'CameraManager']