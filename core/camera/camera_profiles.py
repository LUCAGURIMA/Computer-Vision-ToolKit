"""
Gerenciador de perfis de configuração de câmera.

Permite salvar, carregar e gerenciar perfis de parâmetros de câmera.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from core.utils.logger import log

class CameraProfileManager:
    """Gerencia perfis de configuração de câmera"""
    
    def __init__(self, profiles_dir: Optional[Path] = None):
        """
        Inicializa o gerenciador de perfis.
        
        Args:
            profiles_dir (Path): Diretório para salvar perfis
        """
        if profiles_dir is None:
            profiles_dir = Path(__file__).parent.parent.parent / "data" / "camera_profiles"
        
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        
        log.info(f"📁 Gerenciador de perfis de câmera: {self.profiles_dir}")
    
    def create_profile(self, profile_name: str, camera_type: str, parameters: Dict[str, Any]) -> bool:
        """
        Cria um novo perfil de configuração.
        
        Args:
            profile_name (str): Nome do perfil
            camera_type (str): Tipo de câmera (basler, webcam, etc)
            parameters (Dict): Parâmetros da câmera
            
        Returns:
            bool: True se criado com sucesso
        """
        try:
            # Valida nome
            if not profile_name or len(profile_name.strip()) == 0:
                log.error("Nome do perfil não pode estar vazio")
                return False
            
            # Remove caracteres especiais do nome
            safe_name = "".join(c if c.isalnum() or c in "_- " else "" for c in profile_name)
            if not safe_name:
                log.error("Nome do perfil inválido")
                return False
            
            profile_path = self.profiles_dir / f"{safe_name}.json"
            
            # Evita sobrescrever perfil existente
            if profile_path.exists():
                log.warning(f"Perfil '{safe_name}' já existe")
                return False
            
            # Estrutura do perfil
            profile_data = {
                "name": profile_name,
                "camera_type": camera_type,
                "parameters": parameters,
                "created_at": str(Path.cwd() / "data"),  # Apenas para referência
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }
            
            # Salva em JSON
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, indent=2, ensure_ascii=False)
            
            log.info(f"✅ Perfil criado: {profile_name}")
            return True
        
        except Exception as e:
            log.error(f"❌ Erro ao criar perfil: {e}")
            return False
    
    def load_profile(self, profile_name: str) -> Optional[Dict[str, Any]]:
        """
        Carrega um perfil existente.
        
        Args:
            profile_name (str): Nome do perfil
            
        Returns:
            Dict com dados do perfil, ou None se não encontrado
        """
        try:
            # Remove .json se incluído
            name = profile_name.replace(".json", "")
            profile_path = self.profiles_dir / f"{name}.json"
            
            if not profile_path.exists():
                log.warning(f"Perfil não encontrado: {profile_name}")
                return None
            
            with open(profile_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            log.info(f"✅ Perfil carregado: {profile_name}")
            return data
        
        except Exception as e:
            log.error(f"❌ Erro ao carregar perfil: {e}")
            return None
    
    def delete_profile(self, profile_name: str) -> bool:
        """
        Deleta um perfil.
        
        Args:
            profile_name (str): Nome do perfil
            
        Returns:
            bool: True se deletado com sucesso
        """
        try:
            name = profile_name.replace(".json", "")
            profile_path = self.profiles_dir / f"{name}.json"
            
            if not profile_path.exists():
                log.warning(f"Perfil não encontrado: {profile_name}")
                return False
            
            profile_path.unlink()
            log.info(f"✅ Perfil deletado: {profile_name}")
            return True
        
        except Exception as e:
            log.error(f"❌ Erro ao deletar perfil: {e}")
            return False
    
    def list_profiles(self, camera_type: Optional[str] = None) -> List[str]:
        """
        Lista perfis disponíveis.
        
        Args:
            camera_type (str): Se especificado, filtra por tipo de câmera
            
        Returns:
            List de nomes de perfis
        """
        try:
            profiles = []
            
            for profile_file in self.profiles_dir.glob("*.json"):
                if camera_type:
                    # Filtra por tipo
                    try:
                        with open(profile_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        if data.get("camera_type") == camera_type:
                            profiles.append(profile_file.stem)
                    except:
                        continue
                else:
                    profiles.append(profile_file.stem)
            
            return sorted(profiles)
        
        except Exception as e:
            log.error(f"❌ Erro ao listar perfis: {e}")
            return []
    
    def profile_exists(self, profile_name: str) -> bool:
        """Verifica se um perfil existe"""
        name = profile_name.replace(".json", "")
        return (self.profiles_dir / f"{name}.json").exists()
    
    def rename_profile(self, old_name: str, new_name: str) -> bool:
        """
        Renomeia um perfil.
        
        Args:
            old_name (str): Nome atual
            new_name (str): Novo nome
            
        Returns:
            bool: True se renomeado com sucesso
        """
        try:
            old_path = self.profiles_dir / f"{old_name}.json"
            new_path = self.profiles_dir / f"{new_name}.json"
            
            if not old_path.exists():
                log.warning(f"Perfil não encontrado: {old_name}")
                return False
            
            if new_path.exists():
                log.warning(f"Perfil já existe: {new_name}")
                return False
            
            # Carrega, atualiza nome, salva com novo nome
            with open(old_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            data["name"] = new_name
            
            with open(new_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            old_path.unlink()
            log.info(f"✅ Perfil renomeado: {old_name} → {new_name}")
            return True
        
        except Exception as e:
            log.error(f"❌ Erro ao renomear perfil: {e}")
            return False
