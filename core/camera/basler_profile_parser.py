"""
Parser para arquivos de perfil Basler (.pfs).

Converte arquivos GenAPI persistence (.pfs) para dicionários Python
e vice-versa.
"""

import re
from typing import Dict, Any, Optional
from pathlib import Path
from core.utils.logger import log


class BaslerProfileParser:
    """
    Parser para arquivos de perfil Basler (.pfs).

    Formato .pfs:
    - Linhas comentadas começam com #
    - Parâmetros: Nome	Valor
    - Parâmetros com seletores: Nome	{Seletor=Valor}	Valor
    """

    def __init__(self):
        self._log_prefix = "[BaslerProfileParser]"

    def parse_pfs_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Parseia um arquivo .pfs e retorna dicionário com parâmetros.

        Args:
            file_path: Caminho para o arquivo .pfs

        Returns:
            Dict com parâmetros ou None se erro
        """
        try:
            if not file_path.exists():
                log.error(f"{self._log_prefix} Arquivo não encontrado: {file_path}")
                return None

            parameters = {}
            metadata = {}

            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()

                    # Ignora linhas vazias
                    if not line:
                        continue

                    # Processa comentários (metadata)
                    if line.startswith('#'):
                        self._parse_comment(line, metadata)
                        continue

                    # Processa parâmetros
                    param = self._parse_parameter_line(line)
                    if param:
                        key, value = param
                        parameters[key] = value
                    else:
                        log.warning(f"{self._log_prefix} Linha inválida {line_num}: {line}")

            result = {
                "metadata": metadata,
                "parameters": parameters,
                "file_info": {
                    "path": str(file_path),
                    "size": file_path.stat().st_size,
                    "modified": file_path.stat().st_mtime
                }
            }

            log.info(f"{self._log_prefix} Arquivo parseado: {len(parameters)} parâmetros")
            return result

        except Exception as e:
            log.error(f"{self._log_prefix} Erro ao parsear arquivo: {e}")
            return None

    def _parse_comment(self, line: str, metadata: Dict[str, Any]):
        """Parseia linha de comentário para extrair metadata"""
        line = line.lstrip('#').strip()

        # Metadata específica do Basler
        if line.startswith('{') and '}' in line:
            # GUID ou outras informações estruturadas
            metadata['device_info'] = line
        elif 'GenApi persistence file' in line:
            # Versão do arquivo
            version_match = re.search(r'version (\d+\.\d+\.\d+)', line)
            if version_match:
                metadata['genapi_version'] = version_match.group(1)
        elif 'Device =' in line:
            # Informações do dispositivo
            device_match = re.search(r'Device = (.+)', line)
            if device_match:
                metadata['device'] = device_match.group(1).strip()
        elif 'Product GUID =' in line:
            # GUID do produto
            guid_match = re.search(r'Product GUID = ([A-F0-9-]+)', line)
            if guid_match:
                metadata['product_guid'] = guid_match.group(1)

    def _parse_parameter_line(self, line: str) -> Optional[tuple]:
        """
        Parseia linha de parâmetro.

        Formatos suportados:
        - Nome	Valor
        - Nome	{Seletor=Valor}	Valor
        """
        parts = line.split('\t')

        if len(parts) < 2:
            return None

        param_name = parts[0].strip()

        # Verifica se tem seletor
        if len(parts) >= 3 and parts[1].startswith('{') and '}' in parts[1]:
            # Formato com seletor: Nome	{Seletor=Valor}	Valor
            selector = parts[1].strip('{}')
            value = parts[2].strip()
            param_key = f"{param_name}@{{{selector}}}"
            return param_key, value
        else:
            # Formato simples: Nome	Valor
            value = parts[1].strip()
            return param_name, value

    def create_pfs_content(self, parameters: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Cria conteúdo de arquivo .pfs a partir de parâmetros.

        Args:
            parameters: Dict com parâmetros
            metadata: Dict com metadata opcional

        Returns:
            String com conteúdo do arquivo .pfs
        """
        lines = []

        # Cabeçalho
        lines.append("# {05D8C294-F295-4dfb-9D01-096BD04049F4}")
        lines.append("# GenApi persistence file (version 3.5.0)")

        # Metadata do dispositivo
        if metadata:
            if 'device' in metadata:
                lines.append(f"# Device = {metadata['device']}")
            if 'product_guid' in metadata:
                lines.append(f"# Product GUID = {metadata['product_guid']}")
            if 'product_version_guid' in metadata:
                lines.append(f"# Product version GUID = {metadata['product_version_guid']}")

        lines.append("")  # Linha vazia

        # Parâmetros ordenados
        for param_key, value in sorted(parameters.items()):
            if '@{' in param_key and param_key.endswith('}'):
                # Parâmetro com seletor: Nome@{Seletor=Valor}
                param_name, selector_part = param_key.split('@', 1)
                selector = selector_part.strip('{}')
                lines.append(f"{param_name}\t{{{selector}}}\t{value}")
            else:
                # Parâmetro simples
                lines.append(f"{param_key}\t{value}")

        return '\n'.join(lines)

    def save_pfs_file(self, file_path: Path, parameters: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Salva parâmetros em arquivo .pfs.

        Args:
            file_path: Caminho onde salvar
            parameters: Parâmetros a salvar
            metadata: Metadata opcional

        Returns:
            bool: True se salvo com sucesso
        """
        try:
            content = self.create_pfs_content(parameters, metadata)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            log.info(f"{self._log_prefix} Arquivo salvo: {file_path}")
            return True

        except Exception as e:
            log.error(f"{self._log_prefix} Erro ao salvar arquivo: {e}")
            return False

    def get_parameter_value(self, parsed_data: Dict[str, Any], param_name: str, selector: Optional[str] = None) -> Optional[str]:
        """
        Obtém valor de parâmetro específico.

        Args:
            parsed_data: Dados parseados do arquivo .pfs
            param_name: Nome do parâmetro
            selector: Seletor opcional

        Returns:
            Valor do parâmetro ou None
        """
        parameters = parsed_data.get('parameters', {})

        if selector:
            param_key = f"{param_name}@{{{selector}}}"
        else:
            param_key = param_name

        return parameters.get(param_key)

    def set_parameter_value(self, parsed_data: Dict[str, Any], param_name: str, value: str, selector: Optional[str] = None):
        """
        Define valor de parâmetro específico.

        Args:
            parsed_data: Dados parseados do arquivo .pfs
            param_name: Nome do parâmetro
            value: Novo valor
            selector: Seletor opcional
        """
        parameters = parsed_data.setdefault('parameters', {})

        if selector:
            param_key = f"{param_name}@{{{selector}}}"
        else:
            param_key = param_name

        parameters[param_key] = value

    def get_all_parameters_by_name(self, parsed_data: Dict[str, Any], param_name: str) -> Dict[str, str]:
        """
        Obtém todos os valores de um parâmetro (todas as variações com seletores).

        Args:
            parsed_data: Dados parseados
            param_name: Nome base do parâmetro

        Returns:
            Dict com seletor -> valor
        """
        parameters = parsed_data.get('parameters', {})
        result = {}

        for key, value in parameters.items():
            if key == param_name or key.startswith(f"{param_name}@{{"):
                if '@{' in key and key.endswith('}'):
                    selector = key.split('@', 1)[1]
                    result[selector] = value
                else:
                    result['default'] = value

        return result