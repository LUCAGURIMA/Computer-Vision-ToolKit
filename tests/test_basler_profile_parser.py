"""
Testes para BaslerProfileParser.
"""

import pytest
import tempfile
from pathlib import Path
from core.camera.basler_profile_parser import BaslerProfileParser


@pytest.fixture
def parser():
    """Instância do parser para testes"""
    return BaslerProfileParser()


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
def temp_pfs_file(sample_pfs_content):
    """Arquivo .pfs temporário para testes"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.pfs', delete=False) as f:
        f.write(sample_pfs_content)
        temp_path = Path(f.name)
    yield temp_path
    temp_path.unlink()


class TestBaslerProfileParser:

    def test_parse_pfs_file_basic(self, parser, temp_pfs_file):
        """Testa parsing básico de arquivo .pfs"""
        result = parser.parse_pfs_file(temp_pfs_file)

        assert result is not None
        assert 'parameters' in result
        assert 'metadata' in result
        assert 'file_info' in result

    def test_parse_parameters_simple(self, parser, temp_pfs_file):
        """Testa parsing de parâmetros simples"""
        result = parser.parse_pfs_file(temp_pfs_file)

        parameters = result['parameters']
        assert parameters['GainAuto'] == 'Off'
        assert parameters['PixelFormat'] == 'BayerRG8'
        assert parameters['Width'] == '4024'
        assert parameters['Height'] == '3036'

    def test_parse_parameters_with_selector(self, parser, temp_pfs_file):
        """Testa parsing de parâmetros com seletor"""
        result = parser.parse_pfs_file(temp_pfs_file)

        parameters = result['parameters']
        assert 'GainRaw@{GainSelector=All}' in parameters
        assert parameters['GainRaw@{GainSelector=All}'] == '0'

    def test_parse_metadata(self, parser, temp_pfs_file):
        """Testa parsing de metadata"""
        result = parser.parse_pfs_file(temp_pfs_file)

        metadata = result['metadata']
        assert 'device' in metadata
        assert 'genapi_version' in metadata

    def test_get_parameter_value_simple(self, parser, temp_pfs_file):
        """Testa obtenção de valor de parâmetro simples"""
        result = parser.parse_pfs_file(temp_pfs_file)

        value = parser.get_parameter_value(result, 'PixelFormat')
        assert value == 'BayerRG8'

    def test_get_parameter_value_with_selector(self, parser, temp_pfs_file):
        """Testa obtenção de valor de parâmetro com seletor"""
        result = parser.parse_pfs_file(temp_pfs_file)

        value = parser.get_parameter_value(result, 'GainRaw', 'GainSelector=All')
        assert value == '0'

    def test_set_parameter_value_simple(self, parser, temp_pfs_file):
        """Testa definição de valor de parâmetro simples"""
        result = parser.parse_pfs_file(temp_pfs_file)

        parser.set_parameter_value(result, 'PixelFormat', 'Mono8')

        value = parser.get_parameter_value(result, 'PixelFormat')
        assert value == 'Mono8'

    def test_set_parameter_value_with_selector(self, parser, temp_pfs_file):
        """Testa definição de valor de parâmetro com seletor"""
        result = parser.parse_pfs_file(temp_pfs_file)

        parser.set_parameter_value(result, 'GainRaw', '100', 'GainSelector=All')

        value = parser.get_parameter_value(result, 'GainRaw', 'GainSelector=All')
        assert value == '100'

    def test_get_all_parameters_by_name(self, parser, temp_pfs_file):
        """Testa obtenção de todas as variações de um parâmetro"""
        result = parser.parse_pfs_file(temp_pfs_file)

        # Adiciona mais variações do mesmo parâmetro
        parser.set_parameter_value(result, 'GainRaw', '50', 'GainSelector=Red')
        parser.set_parameter_value(result, 'GainRaw', '75', 'GainSelector=Green')

        variations = parser.get_all_parameters_by_name(result, 'GainRaw')

        assert '{GainSelector=All}' in variations
        assert '{GainSelector=Red}' in variations
        assert '{GainSelector=Green}' in variations
        assert variations['{GainSelector=All}'] == '0'
        assert variations['{GainSelector=Red}'] == '50'
        assert variations['{GainSelector=Green}'] == '75'

    def test_create_pfs_content(self, parser):
        """Testa criação de conteúdo .pfs"""
        parameters = {
            'GainAuto': 'Off',
            'PixelFormat': 'BayerRG8',
            'Width': '4024',
            'GainRaw@{GainSelector=All}': '100'
        }

        metadata = {
            'device': 'Basler::GigECamera',
            'genapi_version': '3.5.0'
        }

        content = parser.create_pfs_content(parameters, metadata)

        # Verifica estrutura básica
        assert content.startswith('# {05D8C294-F295-4dfb-9D01-096BD04049F4}')
        assert 'GenApi persistence file' in content
        assert 'Device = Basler::GigECamera' in content
        assert 'GainAuto\tOff' in content
        assert 'GainRaw\t{GainSelector=All}\t100' in content

    def test_save_and_load_pfs_file(self, parser, tmp_path):
        """Testa salvar e carregar arquivo .pfs"""
        # Dados de teste
        parameters = {
            'GainAuto': 'Off',
            'PixelFormat': 'BayerRG8',
            'ExposureTimeRaw': '10000',
            'GainRaw@{GainSelector=All}': '50'
        }

        metadata = {
            'device': 'Test Camera',
            'genapi_version': '3.5.0'
        }

        # Salva arquivo
        file_path = tmp_path / "test_profile.pfs"
        success = parser.save_pfs_file(file_path, parameters, metadata)
        assert success is True
        assert file_path.exists()

        # Carrega arquivo
        loaded = parser.parse_pfs_file(file_path)
        assert loaded is not None

        # Verifica parâmetros
        loaded_params = loaded['parameters']
        assert loaded_params['GainAuto'] == 'Off'
        assert loaded_params['PixelFormat'] == 'BayerRG8'
        assert loaded_params['GainRaw@{GainSelector=All}'] == '50'

        # Verifica metadata
        loaded_meta = loaded['metadata']
        assert loaded_meta['device'] == 'Test Camera'

    def test_parse_nonexistent_file(self, parser):
        """Testa parsing de arquivo inexistente"""
        result = parser.parse_pfs_file(Path("nonexistent.pfs"))
        assert result is None

    def test_save_pfs_file_invalid_path(self, parser):
        """Testa salvar em caminho inválido"""
        success = parser.save_pfs_file(Path("/invalid/path/test.pfs"), {})
        assert success is False