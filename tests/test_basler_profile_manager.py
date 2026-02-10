"""
Testes para BaslerProfileManager.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch
from core.camera.basler_profile_manager import BaslerProfileManager


@pytest.fixture
def manager(tmp_path):
    """Instância do manager para testes"""
    profiles_dir = tmp_path / "profiles"
    return BaslerProfileManager(profiles_dir)


@pytest.fixture
def sample_pfs_content():
    """Conteúdo de exemplo de arquivo .pfs"""
    return """# {05D8C294-F295-4dfb-9D01-096BD04049F4}
# GenApi persistence file (version 3.5.0)
# Device = Basler::GigECamera -- Basler generic GigEVision camera interface
GainAuto	Off
GainRaw	{GainSelector=All}	0
PixelFormat	BayerRG8
Width	4024
Height	3036
ExposureTimeRaw	10010
"""


@pytest.fixture
def temp_pfs_file(tmp_path, sample_pfs_content):
    """Arquivo .pfs temporário"""
    pfs_file = tmp_path / "test_camera.pfs"
    pfs_file.write_text(sample_pfs_content)
    return pfs_file


class TestBaslerProfileManager:

    def test_initialization(self, manager):
        """Testa inicialização do manager"""
        assert manager.profiles_dir.exists()
        assert manager.parser is not None

    def test_load_pfs_profile(self, manager, temp_pfs_file):
        """Testa carregamento de arquivo .pfs"""
        success = manager.load_pfs_profile(temp_pfs_file, "test_profile")

        assert success is True
        assert manager.profile_exists("test_profile")

        # Verifica se foi convertido corretamente
        profile = manager.load_profile("test_profile")
        assert profile is not None
        assert profile["camera_type"] == "basler"

        # Verifica parâmetros (estão na chave "parameters")
        assert profile["parameters"]["GainAuto"] == "Off"
        assert profile["parameters"]["PixelFormat"] == "BayerRG8"
        assert profile["parameters"]["Width"] == "4024"

    def test_save_pfs_profile(self, manager, tmp_path):
        """Testa salvamento de perfil como .pfs"""
        # Primeiro cria um perfil
        parameters = {
            "GainAuto": "Off",
            "PixelFormat": "BayerRG8",
            "Width": "4024",
            "Height": "3036"
        }

        success = manager.create_pfs_profile_from_parameters("test_profile", parameters)
        assert success is True

        # Salva como .pfs
        pfs_file = tmp_path / "exported.pfs"
        success = manager.save_pfs_profile("test_profile", pfs_file)

        assert success is True
        assert pfs_file.exists()

        # Verifica conteúdo
        content = pfs_file.read_text()
        assert "GainAuto\tOff" in content
        assert "PixelFormat\tBayerRG8" in content

    def test_modify_pfs_parameter(self, manager):
        """Testa modificação de parâmetro"""
        # Cria perfil
        parameters = {"GainAuto": "Off", "ExposureTimeRaw": "10000"}
        manager.create_pfs_profile_from_parameters("test_profile", parameters)

        # Modifica parâmetro
        success = manager.modify_pfs_parameter("test_profile", "ExposureTimeRaw", "20000")

        assert success is True

        # Verifica modificação
        value = manager.get_pfs_parameter("test_profile", "ExposureTimeRaw")
        assert value == "20000"

    def test_modify_pfs_parameter_with_selector(self, manager):
        """Testa modificação de parâmetro com seletor"""
        # Cria perfil com parâmetro seletor
        parameters = {"GainRaw@{GainSelector=All}": "100"}
        manager.create_pfs_profile_from_parameters("test_profile", parameters)

        # Modifica parâmetro com seletor
        success = manager.modify_pfs_parameter("test_profile", "GainRaw", "200", "GainSelector=All")

        assert success is True

        # Verifica modificação
        value = manager.get_pfs_parameter("test_profile", "GainRaw", "GainSelector=All")
        assert value == "200"

    def test_get_pfs_parameter(self, manager):
        """Testa obtenção de parâmetro"""
        parameters = {"GainAuto": "Off", "PixelFormat": "BayerRG8"}
        manager.create_pfs_profile_from_parameters("test_profile", parameters)

        value = manager.get_pfs_parameter("test_profile", "PixelFormat")
        assert value == "BayerRG8"

    def test_list_pfs_profiles(self, manager):
        """Testa listagem de perfis .pfs"""
        # Cria alguns perfis
        manager.create_pfs_profile_from_parameters("profile1", {"GainAuto": "Off"})
        manager.create_pfs_profile_from_parameters("profile2", {"GainAuto": "Continuous"})
        manager.create_profile("json_profile", "webcam", {"resolution": "640x480"})

        pfs_profiles = manager.list_pfs_profiles()

        assert "profile1" in pfs_profiles
        assert "profile2" in pfs_profiles
        assert "json_profile" not in pfs_profiles

    def test_import_pfs_directory(self, manager, tmp_path):
        """Testa importação de diretório com arquivos .pfs"""
        # Cria diretório com arquivos .pfs
        pfs_dir = tmp_path / "pfs_files"
        pfs_dir.mkdir()

        # Arquivo 1
        pfs1 = pfs_dir / "camera1.pfs"
        pfs1.write_text("""# {05D8C294-F295-4dfb-9D01-096BD04049F4}
GainAuto	Off
PixelFormat	BayerRG8
""")

        # Arquivo 2
        pfs2 = pfs_dir / "camera2.pfs"
        pfs2.write_text("""# {05D8C294-F295-4dfb-9D01-096BD04049F4}
GainAuto	Continuous
PixelFormat	Mono8
""")

        # Importa
        imported = manager.import_pfs_directory(pfs_dir)

        assert imported == 2
        assert manager.profile_exists("camera1")
        assert manager.profile_exists("camera2")

    def test_export_pfs_directory(self, manager, tmp_path):
        """Testa exportação de perfis para .pfs"""
        # Cria perfis
        manager.create_pfs_profile_from_parameters("export1", {"GainAuto": "Off"})
        manager.create_pfs_profile_from_parameters("export2", {"GainAuto": "Continuous"})

        # Exporta
        export_dir = tmp_path / "exported"
        exported = manager.export_pfs_directory(export_dir)

        assert exported == 2
        assert (export_dir / "export1.pfs").exists()
        assert (export_dir / "export2.pfs").exists()

    def test_duplicate_pfs_profile(self, manager):
        """Testa duplicação de perfil"""
        # Cria perfil original
        parameters = {"GainAuto": "Off", "PixelFormat": "BayerRG8"}
        manager.create_pfs_profile_from_parameters("original", parameters)

        # Duplica
        success = manager.duplicate_pfs_profile("original", "copy")

        assert success is True
        assert manager.profile_exists("copy")

        # Verifica se dados são iguais (comparando apenas parâmetros da câmera)
        original = manager.load_profile("original")
        copy = manager.load_profile("copy")

        # Remove campos de metadata para comparação
        orig_params = {k: v for k, v in original.items() if k not in ["name", "format", "converted_at", "metadata", "file_info", "timestamp"]}
        copy_params = {k: v for k, v in copy.items() if k not in ["name", "format", "converted_at", "metadata", "file_info", "timestamp"]}
        
        assert orig_params == copy_params

    def test_validate_pfs_profile_valid(self, manager):
        """Testa validação de perfil válido"""
        parameters = {
            "Width": "4024",
            "Height": "3036",
            "PixelFormat": "BayerRG8",
            "ExposureTimeRaw": "10000",
            "GainRaw": "100"
        }
        manager.create_pfs_profile_from_parameters("valid_profile", parameters)

        validation = manager.validate_pfs_profile("valid_profile")

        assert validation["valid"] is True
        assert len(validation["errors"]) == 0
        assert validation["parameters_count"] == 10  # 5 parâmetros originais + 5 campos adicionais (format, metadata, file_info, converted_at, name?)

    def test_validate_pfs_profile_invalid(self, manager):
        """Testa validação de perfil inválido"""
        # Perfil sem parâmetros obrigatórios
        parameters = {"SomeParam": "SomeValue"}
        manager.create_pfs_profile_from_parameters("invalid_profile", parameters)

        validation = manager.validate_pfs_profile("invalid_profile")

        assert validation["valid"] is False
        assert len(validation["errors"]) > 0
        assert "Width" in str(validation["errors"])
        assert "Height" in str(validation["errors"])

    def test_validate_pfs_profile_nonexistent(self, manager):
        """Testa validação de perfil inexistente"""
        validation = manager.validate_pfs_profile("nonexistent")

        assert validation["valid"] is False
        assert len(validation["errors"]) > 0

    def test_create_pfs_profile_from_parameters(self, manager):
        """Testa criação direta de perfil .pfs"""
        parameters = {
            "GainAuto": "Off",
            "PixelFormat": "BayerRG8",
            "Width": "4024"
        }

        metadata = {
            "device": "Test Camera",
            "genapi_version": "3.5.0"
        }

        success = manager.create_pfs_profile_from_parameters(
            "direct_profile", parameters, metadata
        )

        assert success is True
        assert manager.profile_exists("direct_profile")

        # Verifica dados (parâmetros estão em profile["parameters"])
        profile = manager.load_profile("direct_profile")
        assert profile["parameters"]["GainAuto"] == "Off"
        assert profile["parameters"]["PixelFormat"] == "BayerRG8"
        assert profile["parameters"]["metadata"]["device"] == "Test Camera"

    def test_load_pfs_profile_nonexistent_file(self, manager):
        """Testa carregamento de arquivo inexistente"""
        nonexistent = Path("nonexistent.pfs")
        success = manager.load_pfs_profile(nonexistent)

        assert success is False

    def test_save_pfs_profile_nonexistent_profile(self, manager, tmp_path):
        """Testa salvamento de perfil inexistente"""
        pfs_file = tmp_path / "output.pfs"
        success = manager.save_pfs_profile("nonexistent", pfs_file)

        assert success is False
        assert not pfs_file.exists()

    def test_modify_pfs_parameter_nonexistent_profile(self, manager):
        """Testa modificação em perfil inexistente"""
        success = manager.modify_pfs_parameter("nonexistent", "GainAuto", "Off")

        assert success is False