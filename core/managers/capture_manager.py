from typing import Optional, Dict, Any
import numpy as np
from .base_manager import BaseManager
from core.utils.logger import log

class CaptureManager(BaseManager):

    def __init__(self, core, camera_profiles: Optional[Any]=None):
        super().__init__(core)
        self.camera_profiles = camera_profiles
        self.current_image: Optional[np.ndarray] = None
        self.raw_image: Optional[np.ndarray] = None
        self.crop_enabled: bool = False
        self.crop_bbox: Optional[tuple] = None
        self._inspect_after_capture: Optional[str] = None
        self._log('info', 'Manager criado')

    def initialize(self) -> bool:
        try:
            if self.camera_profiles:
                return self.camera_profiles.load_profiles()
            return True
        except Exception as e:
            self._log('error', f'Falha na inicialização: {e}')
            return False

    def cleanup(self) -> None:
        self.clear_images()
        self._log('info', 'Limpeza completa')

    def set_crop_settings(self, enabled: bool, bbox: Optional[tuple]=None):
        self.crop_enabled = enabled
        self.crop_bbox = bbox
        if enabled:
            self._log('info', f'Crop habilitado: {bbox}')
        else:
            self._log('info', 'Crop desabilitado')

    def reset_crop(self):
        self.crop_enabled = False
        self.crop_bbox = None
        self._log('info', 'Crop resetado')

    def set_inspect_after_capture(self, inspection_type: Optional[str]=None):
        self._inspect_after_capture = inspection_type
        if inspection_type:
            self._log('debug', f'Inspeção após captura: {inspection_type}')

    def process_captured_image(self, capture_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            raw_image = capture_result.get('image')
            camera_info = capture_result.get('camera_info', {})
            timestamp = capture_result.get('timestamp', '')
            if raw_image is None:
                raise Exception('Nenhuma imagem no resultado de captura')
            self.raw_image = raw_image
            crop_applied = False
            processed_image = raw_image
            if self.crop_enabled and self.crop_bbox:
                try:
                    ops = [{'name': 'crop', 'bbox': self.crop_bbox}]
                    processed_image = self.core.preprocess_image(raw_image, ops)
                    crop_applied = True
                    self._log('debug', f'Crop aplicado: {self.crop_bbox}')
                except Exception as e:
                    self._log('error', f'Falha ao aplicar crop: {e}')
                    raise Exception(f'Falha ao aplicar crop: {e}')
            self.current_image = processed_image
            result = {'image': processed_image, 'raw_image': raw_image, 'camera_info': camera_info, 'timestamp': timestamp, 'shape': processed_image.shape, 'crop_applied': crop_applied}
            self._notify('capture_completed', {'shape': processed_image.shape, 'crop_applied': crop_applied})
            self._log('info', f'Imagem processada: {processed_image.shape}')
            return result
        except Exception as e:
            self._log('error', f'Erro ao processar imagem: {e}')
            self._notify('capture_error', {'error': str(e)})
            return None

    def get_current_image(self) -> Optional[np.ndarray]:
        return self.current_image

    def get_raw_image(self) -> Optional[np.ndarray]:
        return self.raw_image

    def get_image_info(self) -> Dict[str, Any]:
        if self.current_image is None:
            return {'shape': None, 'dtype': None, 'size_mb': 0, 'crop_applied': False, 'status': 'Nenhuma imagem'}
        shape = self.current_image.shape
        dtype = str(self.current_image.dtype)
        size_mb = self.current_image.nbytes / (1024 * 1024)
        return {'shape': shape, 'dtype': dtype, 'size_mb': size_mb, 'crop_applied': self.crop_enabled, 'crop_bbox': self.crop_bbox if self.crop_enabled else None, 'status': 'OK'}

    def clear_images(self):
        self.current_image = None
        self.raw_image = None
        self._inspect_after_capture = None
        self._log('debug', 'Imagens limpas')

    def should_inspect_after_capture(self) -> Optional[str]:
        return self._inspect_after_capture

    def apply_profile(self, profile_name: str) -> bool:
        if not self.camera_profiles:
            self._log('warning', 'Nenhum camera_profiles disponível')
            return False
        try:
            if hasattr(self.camera_profiles, 'load_profile'):
                profile = self.camera_profiles.load_profile(profile_name)
            else:
                profile = getattr(self.camera_profiles, 'get_profile', lambda n: None)(profile_name)
            if not profile:
                self._log('error', f'Perfil não encontrado: {profile_name}')
                return False
            params = profile.get('parameters', {})
            if not isinstance(params, dict):
                self._log('warning', 'Parâmetros do perfil mal formatados')
                params = {}
            camera_obj = None
            if hasattr(self.core, 'camera_manager'):
                cam_mgr = self.core.camera_manager
                camera_obj = getattr(cam_mgr, 'active_camera', None) or getattr(cam_mgr, 'camera', None)
            applied_any = False
            applied_list = []
            skipped_list = []

            def normalize(name: str) -> str:
                base = name.split('@')[0]
                if '/' in base:
                    base = base.split('/')[-1]
                import re
                s1 = re.sub('(.)([A-Z][a-z]+)', '\\1_\\2', base)
                snake = re.sub('([a-z0-9])([A-Z])', '\\1_\\2', s1).lower()
                return snake

            def parse_selectors(param_key: str) -> tuple[str, dict]:
                if '@' not in param_key:
                    return (param_key, {})
                base, selector_part = param_key.split('@', 1)
                selectors = {}
                if selector_part.startswith('{') and selector_part.endswith('}'):
                    content = selector_part[1:-1]
                    for pair in content.split(','):
                        if '=' in pair:
                            key, val = pair.split('=', 1)
                            selectors[key.strip()] = val.strip()
                return (base, selectors)
            mapping = {'acquisition_frame_rate': 'frame_rate', 'balancewhiteauto': 'balance_white', 'balance_white_auto': 'balance_white'}
            if isinstance(camera_obj, object) and hasattr(camera_obj, 'apply_pfs_file') and profile.get('_pfs_file'):
                pfs_path = profile.get('_pfs_file')
                self._log('debug', f'Delegando aplicação .pfs direto para câmera: {pfs_path}')
                try:
                    result = camera_obj.apply_pfs_file(pfs_path)
                    return bool(result)
                except Exception as e:
                    self._log('error', f'Falha ao aplicar .pfs via câmera: {e}')
            for key, val in params.items():
                if key in ['format', 'metadata', 'file_info', 'converted_at']:
                    continue
                param_name, selectors = parse_selectors(key)
                norm = normalize(param_name)
                norm = mapping.get(norm, norm)
                selector_applied_ok = True
                for sel_key in sorted(selectors.keys()):
                    sel_val = selectors[sel_key]
                    sel_norm = normalize(sel_key)
                    if camera_obj and hasattr(camera_obj, 'set_parameter'):
                        try:
                            success = camera_obj.set_parameter(sel_norm, str(sel_val))
                            self._log('debug', f'Seletor {sel_norm}={sel_val} -> {success}')
                            if not success:
                                selector_applied_ok = False
                                self._log('debug', f'Seletor {sel_norm} não pôde ser aplicado')
                        except Exception as e:
                            self._log('debug', f'Erro ao aplicar seletor {sel_norm}: {e}')
                            selector_applied_ok = False
                if not selector_applied_ok and selectors:
                    self._log('debug', f'Pulando {norm} pois seletores falharam')
                    skipped_list.append(norm)
                    continue
                if camera_obj and hasattr(camera_obj, 'set_parameter'):
                    try:
                        success = camera_obj.set_parameter(norm, str(val))
                        self._log('debug', f'Aplicando {norm}={val} -> {success}')
                        if success:
                            applied_any = True
                            applied_list.append(f'{norm}={val}')
                        else:
                            skipped_list.append(norm)
                    except Exception as e:
                        self._log('error', f'Erro ajustando parâmetro {norm}: {e}')
                        skipped_list.append(norm)
                else:
                    self._log('warning', f'Nenhuma câmera ou método set_parameter não disponível para {norm}')
                    skipped_list.append(norm)
            if applied_any:
                self._log('info', f"Perfil '{profile_name}' aplicado: {len(applied_list)} parâmetro(s) ajustado(s)")
                self._log('debug', f'Parâmetros aplicados: {applied_list}')
            else:
                self._log('warning', f"Perfil '{profile_name}' não alterou nenhum parâmetro")
            if skipped_list:
                self._log('debug', f'Parâmetros pulados/inválidos: {skipped_list}')
            return applied_any
        except Exception as e:
            self._log('error', f'Erro ao aplicar perfil: {e}')
            return False