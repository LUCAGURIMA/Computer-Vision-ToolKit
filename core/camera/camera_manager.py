from typing import List, Optional, Dict, Any
import numpy as np
from .icamera import ICamera
try:
    from .basler_camera import BaslerCamera
except Exception as e:
    print(f'  Erro ao importar BaslerCamera: {e}')
    BaslerCamera = None
from .webcam_camera import WebcamCamera
from .mock_camera import MockCamera
from core.utils.logger import log
from config import CAMERA_CONFIG

class CameraManager:

    def __init__(self, config: Optional[Dict[str, Any]]=None):
        self.config = config or CAMERA_CONFIG
        self.cameras: List[ICamera] = []
        self.active_camera: Optional[ICamera] = None
        self._current_index = -1
        log.info(' Inicializando CameraManager...')
        self._create_camera_chain()

    def _create_camera_chain(self):
        if 'primary' in self.config and BaslerCamera is not None:
            primary_config = self.config['primary']
            if primary_config['type'] == 'basler':
                try:
                    camera = BaslerCamera(ip_address=primary_config.get('ip'))
                    self.cameras.append(camera)
                    log.info(f' Adicionada câmera principal: Basler')
                except Exception as e:
                    log.warning(f'  Erro ao criar câmera Basler: {e}')
        elif 'primary' in self.config:
            log.warning('  Câmera primária (Basler) configurada mas não disponível')
        else:
            log.warning('  Nenhuma câmera primária configurada em settings.py')
        for i, fb_config in enumerate(self.config.get('fallbacks', [])):
            camera_type = fb_config['type']
            if camera_type == 'webcam':
                camera = WebcamCamera(camera_index=fb_config.get('index', 0))
                self.cameras.append(camera)
                log.info(f' Adicionada fallback {i + 1}: Webcam')
            elif camera_type == 'mock':
                camera = MockCamera(image_path=fb_config.get('image_path'))
                self.cameras.append(camera)
                log.info(f' Adicionada fallback {i + 1}: MockCamera')
        log.info(f' Total de câmeras na cadeia: {len(self.cameras)}')

    def initialize(self) -> bool:
        max_retries = self.config.get('primary', {}).get('max_retries', 3)
        for i, camera in enumerate(self.cameras):
            log.info(f' Tentando inicializar câmera {i + 1}/{len(self.cameras)}: {camera.__class__.__name__}')
            for attempt in range(max_retries):
                try:
                    log.debug(f'  Tentativa {attempt + 1}/{max_retries}...')
                    if camera.initialize():
                        self.active_camera = camera
                        self._current_index = i
                        info = camera.get_info()
                        log.info(f' Câmera ativa: {camera.__class__.__name__}')
                        log.info(f"   Tipo: {info.get('type', 'N/A')}")
                        if 'model' in info:
                            log.info(f"   Modelo: {info['model']}")
                        if 'width' in info and 'height' in info:
                            log.info(f"   Resolução: {info['width']}x{info['height']}")
                        return True
                except Exception as e:
                    log.warning(f'  Tentativa {attempt + 1} falhou: {e}')
                    if attempt < max_retries - 1:
                        log.debug('  Aguardando 1 segundo antes de tentar novamente...')
                        import time
                        time.sleep(1)
                    else:
                        log.error(f' Todas as tentativas falharam para {camera.__class__.__name__}')
            log.warning(f'  {camera.__class__.__name__} não pôde ser inicializada')
        log.error(' TODAS as câmeras falharam!')
        return False

    def capture(self) -> Optional[np.ndarray]:
        if self.active_camera is None:
            raise RuntimeError('Nenhuma câmera inicializada. Chame initialize() primeiro.')
        try:
            image = self.active_camera.capture()
            if image is not None:
                return image
            else:
                log.warning('Câmera ativa retornou None, tentando fallback...')
                raise RuntimeError('Captura falhou')
        except Exception as e:
            log.warning(f' Câmera ativa falhou: {e}')
            return self._try_next_camera()

    def _try_next_camera(self) -> Optional[np.ndarray]:
        if self._current_index + 1 >= len(self.cameras):
            log.error(' Nenhuma câmera restante na cadeia!')
            return None
        if self.active_camera:
            self.active_camera.release()
        self._current_index += 1
        self.active_camera = self.cameras[self._current_index]
        log.info(f' Alternando para câmera {self._current_index + 1}/{len(self.cameras)}: {self.active_camera.__class__.__name__}')
        try:
            if self.active_camera.initialize():
                return self.active_camera.capture()
            else:
                return self._try_next_camera()
        except Exception as e:
            log.error(f'Falha ao alternar câmera: {e}')
            return self._try_next_camera()

    def get_active_camera_info(self) -> Dict[str, Any]:
        if self.active_camera:
            info = self.active_camera.get_info()
            info['index'] = self._current_index
            info['total_cameras'] = len(self.cameras)
            return info
        return {'status': 'no_active_camera'}

    def get_all_cameras_info(self) -> List[Dict[str, Any]]:
        infos = []
        for i, camera in enumerate(self.cameras):
            info = camera.get_info()
            info['position'] = i
            info['is_active'] = i == self._current_index
            info['connected'] = camera._initialized if hasattr(camera, '_initialized') else False
            infos.append(info)
        return infos

    def detect_all_cameras(self) -> List[Dict[str, Any]]:
        infos = []
        for i, camera in enumerate(self.cameras):
            camera_info = {'position': i, 'type': camera.__class__.__name__.replace('Camera', '').lower(), 'is_active': i == self._current_index, 'connected': False, 'available': False}
            try:
                if camera.__class__.__name__ == 'MockCamera':
                    camera_info['available'] = True
                    camera_info['connected'] = hasattr(camera, '_initialized') and camera._initialized
                    if camera_info['connected']:
                        camera_info.update(camera.get_info())
                    else:
                        camera_info.update({'model': 'Mock (Simulada)', 'width': 640, 'height': 480})
                elif hasattr(camera, '_initialized') and camera._initialized:
                    camera_info['connected'] = True
                    camera_info['available'] = True
                    camera_info.update(camera.get_info())
                else:
                    if hasattr(camera, 'test_connection'):
                        if camera.test_connection():
                            camera_info['available'] = True
                    elif camera.__class__.__name__ == 'WebcamCamera':
                        camera_info['available'] = True
                    if camera_info['available']:
                        try:
                            camera_info.update(camera.get_info())
                        except:
                            pass
            except Exception as e:
                log.debug(f'Erro ao detectar câmera {i}: {e}')
                camera_info['available'] = False
            infos.append(camera_info)
        return infos

    def release(self):
        for camera in self.cameras:
            try:
                camera.release()
            except:
                pass
        self.active_camera = None
        self._current_index = -1
        log.info(' Todas as câmeras liberadas')
if __name__ == '__main__':
    print('\n' + '=' * 50)
    print(' TESTE DO CAMERA MANAGER')
    print('=' * 50)
    manager = CameraManager()
    if manager.initialize():
        print('\n CameraManager inicializado com sucesso!')
        active_info = manager.get_active_camera_info()
        print(f'\n Câmera ativa:')
        for key, value in active_info.items():
            print(f'  {key}: {value}')
        print('\n Tentando capturar imagem...')
        image = manager.capture()
        if image is not None:
            print(f' Imagem capturada: {image.shape}')
            if active_info.get('type') == 'mock':
                import cv2
                cv2.imwrite('teste_mock_camera.jpg', image)
                print(" Imagem mock salva como 'teste_mock_camera.jpg'")
        else:
            print(' Falha ao capturar imagem')
        manager.release()
    else:
        print(' CameraManager não pôde ser inicializado')
    print('\n' + '=' * 50)
    print(' TESTE COMPLETO')
    print('=' * 50)