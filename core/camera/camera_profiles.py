import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from core.utils.logger import log

class CameraProfileManager:

    def __init__(self, profiles_dir: Optional[Path]=None):
        if profiles_dir is None:
            profiles_dir = Path(__file__).parent.parent.parent / 'data' / 'camera_profiles'
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        log.info(f'📁 Gerenciador de perfis de câmera: {self.profiles_dir}')

    def create_profile(self, profile_name: str, camera_type: str, parameters: Dict[str, Any]) -> bool:
        try:
            if not profile_name or len(profile_name.strip()) == 0:
                log.error('Nome do perfil não pode estar vazio')
                return False
            safe_name = ''.join((c if c.isalnum() or c in '_- ' else '' for c in profile_name))
            if not safe_name:
                log.error('Nome do perfil inválido')
                return False
            profile_path = self.profiles_dir / f'{safe_name}.json'
            if profile_path.exists():
                log.warning(f"Perfil '{safe_name}' já existe")
                return False
            profile_data = {'name': profile_name, 'camera_type': camera_type, 'parameters': parameters, 'created_at': str(Path.cwd() / 'data'), 'timestamp': __import__('datetime').datetime.now().isoformat()}
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, indent=2, ensure_ascii=False)
            log.info(f'✅ Perfil criado: {profile_name}')
            return True
        except Exception as e:
            log.error(f'❌ Erro ao criar perfil: {e}')
            return False

    def load_profile(self, profile_name: str) -> Optional[Dict[str, Any]]:
        try:
            name = profile_name.replace('.json', '').replace('.pfs', '')
            pfs_path = self.profiles_dir / f'{name}.pfs'
            if pfs_path.exists():
                data = {'name': name, 'camera_type': 'basler', 'parameters': {}, '_pfs_file': str(pfs_path), 'format': 'pfs'}
                log.info(f'✅ Perfil .pfs carregado: {name}')
                return data
            json_path = self.profiles_dir / f'{name}.json'
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                log.info(f'✅ Perfil JSON carregado: {profile_name}')
                return data
            log.warning(f'Perfil não encontrado: {profile_name} (.pfs ou .json)')
            return None
        except Exception as e:
            log.error(f'❌ Erro ao carregar perfil: {e}')
            return None

    def delete_profile(self, profile_name: str) -> bool:
        try:
            name = profile_name.replace('.json', '')
            profile_path = self.profiles_dir / f'{name}.json'
            if not profile_path.exists():
                log.warning(f'Perfil não encontrado: {profile_name}')
                return False
            profile_path.unlink()
            log.info(f'✅ Perfil deletado: {profile_name}')
            return True
        except Exception as e:
            log.error(f'❌ Erro ao deletar perfil: {e}')
            return False

    def list_profiles(self, camera_type: Optional[str]=None) -> List[str]:
        try:
            profiles = []
            seen = set()
            for pfs_file in self.profiles_dir.glob('*.pfs'):
                profile_name = pfs_file.stem
                if profile_name not in seen:
                    if camera_type is None or camera_type == 'basler':
                        profiles.append(profile_name)
                        seen.add(profile_name)
                        log.debug(f'Encontrado perfil .pfs: {profile_name}')
            for json_file in self.profiles_dir.glob('*.json'):
                profile_name = json_file.stem
                if profile_name not in seen:
                    if camera_type:
                        try:
                            with open(json_file, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            if data.get('camera_type') == camera_type:
                                profiles.append(profile_name)
                                seen.add(profile_name)
                        except:
                            continue
                    else:
                        profiles.append(profile_name)
                        seen.add(profile_name)
            return sorted(profiles)
        except Exception as e:
            log.error(f'❌ Erro ao listar perfis: {e}')
            return []

    def profile_exists(self, profile_name: str) -> bool:
        name = profile_name.replace('.json', '')
        return (self.profiles_dir / f'{name}.json').exists()

    def rename_profile(self, old_name: str, new_name: str) -> bool:
        try:
            old_path = self.profiles_dir / f'{old_name}.json'
            new_path = self.profiles_dir / f'{new_name}.json'
            if not old_path.exists():
                log.warning(f'Perfil não encontrado: {old_name}')
                return False
            if new_path.exists():
                log.warning(f'Perfil já existe: {new_name}')
                return False
            with open(old_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data['name'] = new_name
            with open(new_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            old_path.unlink()
            log.info(f'✅ Perfil renomeado: {old_name} → {new_name}')
            return True
        except Exception as e:
            log.error(f'❌ Erro ao renomear perfil: {e}')
            return False