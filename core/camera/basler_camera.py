import cv2
import numpy as np
from typing import Dict, Any, Optional
import sys
from core.utils.logger import log
from .icamera import ICamera
try:
    from pypylon import pylon
    BASLER_AVAILABLE = True
    try:
        log.info('Pypylon disponivel - Camera Basler HABILITADA')
    except:
        print('Pypylon disponivel - Camera Basler HABILITADA')
except ImportError:
    BASLER_AVAILABLE = False
    try:
        log.warning('Pypylon nao instalado - Camera Basler DESABILITADA. Instale com: pip install pypylon')
    except:
        print('Pypylon nao instalado - Camera Basler DESABILITADA. Instale com: pip install pypylon')

class BaslerCamera(ICamera):

    def __init__(self, ip_address: Optional[str]=None):
        self.ip_address = ip_address
        self._camera = None
        self._initialized = False
        log.info(f" Câmera Basler criada (IP: {ip_address or 'auto'})")

    def initialize(self) -> bool:
        if not BASLER_AVAILABLE:
            log.error('Pypylon NAO esta instalado! Instale com: pip install pypylon')
            raise RuntimeError('Biblioteca pypylon não disponível. Instale com: pip install pypylon')
        try:
            log.info(' Inicializando câmera Basler...')
            log.debug(f"  IP especificado: {self.ip_address or 'automático (primeira disponível)'}")
            tl_factory = pylon.TlFactory.GetInstance()
            log.debug('  Fábrica de dispositivos obtida')
            devices = tl_factory.EnumerateDevices()
            log.info(f'   Encontradas {len(devices)} câmera(s) Basler')
            if not devices:
                msg = 'Nenhuma camera Basler encontrada.'
                log.error(f'ERRO: {msg}')
                raise RuntimeError(msg)
            for i, device in enumerate(devices):
                model = device.GetModelName() if hasattr(device, 'GetModelName') else 'Desconhecido'
                ip = device.GetIpAddress() if hasattr(device, 'GetIpAddress') else 'N/A'
                log.info(f'     [{i}] {model} (IP: {ip})')
            selected_device = None
            if self.ip_address:
                log.debug(f'  Procurando câmera com IP: {self.ip_address}')
                for device in devices:
                    if hasattr(device, 'GetIpAddress') and device.GetIpAddress() == self.ip_address:
                        selected_device = device
                        log.info(f'  OK - Camera encontrada com IP: {self.ip_address}')
                        break
                if not selected_device:
                    log.warning(f'    IP {self.ip_address} não encontrado, usando primeira câmera')
            if selected_device is None:
                selected_device = devices[0]
                model = selected_device.GetModelName() if hasattr(selected_device, 'GetModelName') else 'Desconhecido'
                log.info(f'   Usando primeira câmera: {model}')
            log.debug('  Criando instância da câmera...')
            self._camera = pylon.InstantCamera(tl_factory.CreateDevice(selected_device))
            log.debug('  Abrindo câmera...')
            self._camera.Open()
            log.debug('  OK - Camera aberta com sucesso')
            log.debug('  Configurando resolução máxima...')
            self._camera.Width.SetValue(self._camera.Width.Max)
            self._camera.Height.SetValue(self._camera.Height.Max)
            width = self._camera.Width.Value
            height = self._camera.Height.Value
            log.info(f'   Resolução: {width}x{height}')
            try:
                self._camera.ExposureAuto.SetValue('Continuous')
                log.info('    Exposição automática ativada')
            except Exception as e:
                log.warning(f'    Não foi possível configurar exposição automática: {e}')
            self._initialized = True
            log.info('OK - Camera Basler inicializada com sucesso!')
            return True
        except Exception as e:
            log.error(f'ERRO - Falha ao inicializar camera Basler: {type(e).__name__}: {e}')
            import traceback
            log.debug(traceback.format_exc())
            self._initialized = False
            return False

    def capture(self) -> Optional[np.ndarray]:
        if not self._initialized or self._camera is None:
            raise RuntimeError('Câmera não inicializada. Chame initialize() primeiro.')
        try:
            log.debug('Capturando imagem da Basler...')
            self._camera.StartGrabbingMax(1)
            grab_result = self._camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            if grab_result.GrabSucceeded():
                image = grab_result.Array
                if len(image.shape) == 2:
                    image = cv2.cvtColor(image, cv2.COLOR_BAYER_BG2BGR)
                grab_result.Release()
                log.debug(f'OK - Imagem capturada: {image.shape}')
                return image
            else:
                grab_result.Release()
                raise RuntimeError('Falha na captura da imagem')
        except Exception as e:
            log.error(f'ERRO - Erro ao capturar imagem: {e}')
            return None

    def release(self):
        if self._camera is not None and self._camera.IsOpen():
            self._camera.Close()
            log.info(' Câmera Basler liberada')
        self._initialized = False

    def get_info(self) -> Dict[str, Any]:
        info = {'type': 'basler', 'ip': self.ip_address, 'initialized': self._initialized, 'available': BASLER_AVAILABLE}
        if self._camera and self._camera.IsOpen():
            info['model'] = self._camera.GetDeviceInfo().GetModelName()
            info['width'] = self._camera.Width.GetValue()
            info['height'] = self._camera.Height.GetValue()
        return info

    def is_available(self) -> bool:
        return BASLER_AVAILABLE

    def get_parameters(self) -> Dict[str, Any]:
        if not self._initialized or not self._camera or (not self._camera.IsOpen()):
            return {}
        try:
            return {'gain': {'value': float(self._camera.Gain.GetValue()) if hasattr(self._camera, 'Gain') else 0, 'type': 'float', 'label': 'Ganho', 'min': 0, 'max': 30, 'step': 0.5, 'description': 'Ganho da câmera (0 a 30 dB)'}, 'exposure_time': {'value': float(self._camera.ExposureTime.GetValue()) if hasattr(self._camera, 'ExposureTime') else 0, 'type': 'float', 'label': 'Tempo de Exposição (µs)', 'min': 26, 'max': 30000000, 'step': 1000, 'description': 'Tempo de exposição em microsegundos (26 µs a 30s)'}, 'frame_rate': {'value': float(self._camera.AcquisitionFrameRate.GetValue()) if hasattr(self._camera, 'AcquisitionFrameRate') else 30, 'type': 'float', 'label': 'Taxa de Quadros (FPS)', 'min': 1, 'max': 200, 'step': 1, 'description': 'Taxa de aquisição em quadros por segundo'}, 'width': {'value': int(self._camera.Width.GetValue()), 'type': 'int', 'label': 'Largura', 'min': 100, 'max': 2048, 'step': 4, 'description': 'Largura da imagem em pixels'}, 'height': {'value': int(self._camera.Height.GetValue()), 'type': 'int', 'label': 'Altura', 'min': 100, 'max': 2048, 'step': 4, 'description': 'Altura da imagem em pixels'}, 'balance_white': {'value': 'auto' if hasattr(self._camera, 'BalanceWhiteAuto') and self._camera.BalanceWhiteAuto.GetValue() == 1 else 'manual', 'type': 'enum', 'label': 'Balanço de Branco', 'options': ['manual', 'auto'], 'description': 'Modo de balanço de branco'}}
        except Exception as e:
            log.debug(f'Erro ao ler parâmetros Basler: {e}')
            return {}

    def set_parameter(self, param_name: str, value: Any) -> bool:
        if not self._initialized or not self._camera or (not self._camera.IsOpen()):
            return False

        def _try_set(node, val) -> bool:

            def _is_writable(n) -> bool:
                try:
                    if hasattr(n, 'GetAccessMode'):
                        mode = n.GetAccessMode()
                        if mode not in (pylon.RW, pylon.WO):
                            return False
                    if hasattr(n, 'IsWritable'):
                        return bool(n.IsWritable())
                except Exception:
                    pass
                return True
            if not _is_writable(node):
                log.debug(f'Basler node not writable, skipping')
                return False
            try:
                node.SetValue(val)
                return True
            except Exception as exc:
                msg = str(exc)
                if 'Node not existing' in msg or 'Expected a string' in msg:
                    log.debug(f'Basler node skipped ({msg})')
                    if 'Expected a string' in msg:
                        try:
                            node.SetValue(str(val))
                            return True
                        except Exception as e2:
                            log.debug(f'Retry with str also failed: {e2}')
                    return False
                raise
        try:
            if param_name == 'gain' and hasattr(self._camera, 'Gain'):
                return _try_set(self._camera.Gain, float(value))
            elif param_name == 'exposure_time' and hasattr(self._camera, 'ExposureTime'):
                return _try_set(self._camera.ExposureTime, int(value))
            elif param_name == 'frame_rate' and hasattr(self._camera, 'AcquisitionFrameRate'):
                return _try_set(self._camera.AcquisitionFrameRate, float(value))
            elif param_name == 'width' and hasattr(self._camera, 'Width'):
                return _try_set(self._camera.Width, int(value))
            elif param_name == 'height' and hasattr(self._camera, 'Height'):
                return _try_set(self._camera.Height, int(value))
            elif param_name == 'balance_white' and hasattr(self._camera, 'BalanceWhiteAuto'):
                mode_val = 1 if str(value).lower() == 'auto' else 0
                return _try_set(self._camera.BalanceWhiteAuto, mode_val)

            def to_pascal(s: str) -> str:
                parts = s.split('_')
                return ''.join((p.capitalize() for p in parts if p))
            tried_names = []
            for candidate in (param_name, to_pascal(param_name)):
                tried_names.append(candidate)
                if hasattr(self._camera, candidate):
                    node = getattr(self._camera, candidate)
                    if _try_set(node, value):
                        log.info(f' Basler: {candidate} = {value} (generic)')
                        return True
            log.debug(f'Parâmetro Basler não reconhecido: {param_name} (tentadas: {tried_names})')
            return False
        except Exception as e:
            msg = str(e)
            if 'Node not existing' in msg or 'Expected a string' in msg:
                log.debug(f'Parâmetro Basler indisponível neste modelo: {msg}')
                return False
            log.error(f'Erro ao ajustar Basler: {e}')
            return False

    def test_connection(self) -> bool:
        if not BASLER_AVAILABLE:
            log.debug('  Pypylon não disponível')
            return False
        try:
            tl_factory = pylon.TlFactory.GetInstance()
            devices = tl_factory.EnumerateDevices()
            available = len(devices) > 0
            if available:
                log.debug(f'  OK - Basler detectada ({len(devices)} camera(s))')
            else:
                log.debug('  ERRO - Nenhuma Basler detectada')
            return available
        except Exception as e:
            log.debug(f'  Erro ao testar Basler: {e}')
            return False

    def apply_pfs_file(self, file_path: str) -> bool:
        if not BASLER_AVAILABLE:
            log.error('Pypylon não disponível, não é possível aplicar .pfs')
            return False
        if not self._initialized or not self._camera or (not self._camera.IsOpen()):
            log.error('Câmera não inicializada, não é possível aplicar .pfs')
            return False
        try:
            pylon.FeaturePersistence.Load(str(file_path), self._camera.GetNodeMap(), True)
            log.info(f'Basler .pfs aplicado via FeaturePersistence: {file_path}')
            return True
        except Exception as e:
            log.error(f'Erro ao aplicar .pfs via pylon: {e}')
            return False
if __name__ == '__main__':
    print(' Testando câmera Basler...')
    camera = BaslerCamera()
    print(f'Disponível: {camera.is_available()}')
    if camera.is_available():
        try:
            if camera.initialize():
                print(f'Info: {camera.get_info()}')
                camera.release()
        except Exception as e:
            print(f'Erro: {e}')
    print(' Teste completo')