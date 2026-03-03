import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from core.camera.camera_profiles import CameraProfileManager
from core.camera.basler_profile_parser import BaslerProfileParser
from core.utils.logger import log

class BaslerProfileManager(CameraProfileManager):

    def __init__(self, profiles_dir: Optional[Path]=None):
        super().__init__(profiles_dir)
        self.parser = BaslerProfileParser()
        log.info('📁 Gerenciador de perfis Basler (.pfs) inicializado')

    def load_pfs_profile(self, pfs_file_path: Path, profile_name: Optional[str]=None) -> bool:
        try:
            if not pfs_file_path.exists():
                log.error(f'Arquivo .pfs não encontrado: {pfs_file_path}')
                return False
            parsed_data = self.parser.parse_pfs_file(pfs_file_path)
            if not parsed_data:
                log.error(f'Falha ao parsear arquivo .pfs: {pfs_file_path}')
                return False
            if profile_name is None:
                profile_name = pfs_file_path.stem
            json_profile = self._pfs_to_json_profile(parsed_data, profile_name)
            json_profile['_pfs_file'] = str(pfs_file_path)
            return self.create_profile(profile_name=profile_name, camera_type='basler', parameters=json_profile)
        except Exception as e:
            log.error(f'Erro ao carregar perfil .pfs: {e}')
            return False

    def save_pfs_profile(self, profile_name: str, pfs_file_path: Path) -> bool:
        try:
            profile_data = self.load_profile(profile_name)
            if not profile_data:
                log.error(f'Perfil não encontrado: {profile_name}')
                return False
            pfs_data = self._json_to_pfs_data(profile_data)
            return self.parser.save_pfs_file(pfs_file_path, pfs_data['parameters'], pfs_data['metadata'])
        except Exception as e:
            log.error(f'Erro ao salvar perfil .pfs: {e}')
            return False

    def modify_pfs_parameter(self, profile_name: str, param_name: str, value: str, selector: Optional[str]=None) -> bool:
        try:
            profile_data = self.load_profile(profile_name)
            if not profile_data:
                return False
            pfs_data = self._json_to_pfs_data(profile_data)
            self.parser.set_parameter_value(pfs_data, param_name, value, selector)
            updated_profile = self._pfs_to_json_profile(pfs_data, profile_name)
            profile_data['parameters'] = updated_profile
            profile_data['timestamp'] = __import__('datetime').datetime.now().isoformat()
            profile_path = self.profiles_dir / f'{profile_name}.json'
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, indent=2, ensure_ascii=False)
            log.info(f'Parâmetro modificado: {param_name} = {value}')
            return True
        except Exception as e:
            log.error(f'Erro ao modificar parâmetro: {e}')
            return False

    def get_pfs_parameter(self, profile_name: str, param_name: str, selector: Optional[str]=None) -> Optional[str]:
        try:
            profile_data = self.load_profile(profile_name)
            if not profile_data:
                return None
            pfs_data = self._json_to_pfs_data(profile_data)
            return self.parser.get_parameter_value(pfs_data, param_name, selector)
        except Exception as e:
            log.error(f'Erro ao obter parâmetro: {e}')
            return None

    def list_pfs_profiles(self) -> List[str]:
        return self.list_profiles(camera_type='basler')

    def import_pfs_directory(self, pfs_directory: Path) -> int:
        if not pfs_directory.exists():
            log.error(f'Diretório não encontrado: {pfs_directory}')
            return 0
        imported_count = 0
        for pfs_file in pfs_directory.glob('*.pfs'):
            profile_name = pfs_file.stem
            if self.load_pfs_profile(pfs_file, profile_name):
                imported_count += 1
        log.info(f'Importados {imported_count} perfis .pfs')
        return imported_count

    def export_pfs_directory(self, export_directory: Path, profile_names: Optional[List[str]]=None) -> int:
        export_directory.mkdir(parents=True, exist_ok=True)
        if profile_names is None:
            profile_names = self.list_pfs_profiles()
        exported_count = 0
        for profile_name in profile_names:
            pfs_file_path = export_directory / f'{profile_name}.pfs'
            if self.save_pfs_profile(profile_name, pfs_file_path):
                exported_count += 1
        log.info(f'Exportados {exported_count} perfis .pfs')
        return exported_count

    def _pfs_to_json_profile(self, pfs_data: Dict[str, Any], profile_name: str) -> Dict[str, Any]:
        json_profile = pfs_data.get('parameters', {}).copy()
        json_profile.update({'format': 'pfs', 'metadata': pfs_data.get('metadata', {}), 'file_info': pfs_data.get('file_info', {}), 'converted_at': __import__('datetime').datetime.now().isoformat()})
        return json_profile

    def _json_to_pfs_data(self, json_profile: Dict[str, Any]) -> Dict[str, Any]:
        profile_params = json_profile.get('parameters', {})
        parameters = {}
        metadata = profile_params.get('metadata', {})
        file_info = profile_params.get('file_info', {})
        for key, value in profile_params.items():
            if key not in ['format', 'metadata', 'file_info', 'converted_at']:
                parameters[key] = value
        return {'metadata': metadata, 'parameters': parameters, 'file_info': file_info}

    def create_pfs_profile_from_parameters(self, profile_name: str, parameters: Dict[str, Any], metadata: Optional[Dict[str, Any]]=None) -> bool:
        try:
            json_profile = parameters.copy()
            json_profile.update({'name': profile_name, 'format': 'pfs', 'metadata': metadata or {}, 'file_info': {}, 'converted_at': __import__('datetime').datetime.now().isoformat()})
            return self.create_profile(profile_name=profile_name, camera_type='basler', parameters=json_profile)
        except Exception as e:
            log.error(f'Erro ao criar perfil .pfs: {e}')
            return False

    def duplicate_pfs_profile(self, source_profile: str, new_profile: str) -> bool:
        try:
            source_data = self.load_profile(source_profile)
            if not source_data:
                return False
            return self.create_profile(profile_name=new_profile, camera_type='basler', parameters=source_data['parameters'])
        except Exception as e:
            log.error(f'Erro ao duplicar perfil: {e}')
            return False

    def validate_pfs_profile(self, profile_name: str) -> Dict[str, Any]:
        result = {'valid': False, 'errors': [], 'warnings': [], 'parameters_count': 0}
        try:
            profile_data = self.load_profile(profile_name)
            if not profile_data:
                result['errors'].append('Perfil não encontrado')
                return result
            parameters = profile_data.get('parameters', {})
            required_params = ['Width', 'Height', 'PixelFormat']
            recommended_params = ['ExposureTimeRaw', 'GainRaw', 'GammaEnable']
            result['parameters_count'] = len(parameters)
            for param in required_params:
                if param not in parameters:
                    result['errors'].append(f'Parâmetro obrigatório ausente: {param}')
            for param in recommended_params:
                if param not in parameters:
                    result['warnings'].append(f'Parâmetro recomendado ausente: {param}')
            if 'Width' in parameters and 'Height' in parameters:
                try:
                    width = int(parameters['Width'])
                    height = int(parameters['Height'])
                    if width <= 0 or height <= 0:
                        result['errors'].append('Dimensões inválidas')
                except ValueError:
                    result['errors'].append('Dimensões não são números válidos')
            if 'PixelFormat' in parameters:
                valid_formats = ['Mono8', 'Mono12', 'BayerRG8', 'BayerRG12', 'RGB8']
                if parameters['PixelFormat'] not in valid_formats:
                    result['warnings'].append(f"Formato de pixel não padrão: {parameters['PixelFormat']}")
            result['valid'] = len(result['errors']) == 0
        except Exception as e:
            result['errors'].append(f'Erro na validação: {str(e)}')
        return result