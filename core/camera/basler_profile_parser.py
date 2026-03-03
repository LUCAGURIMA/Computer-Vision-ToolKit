import re
from typing import Dict, Any, Optional
from pathlib import Path
from core.utils.logger import log

class BaslerProfileParser:

    def __init__(self):
        self._log_prefix = '[BaslerProfileParser]'

    def parse_pfs_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        try:
            if not file_path.exists():
                log.error(f'{self._log_prefix} Arquivo não encontrado: {file_path}')
                return None
            parameters = {}
            metadata = {}
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith('#'):
                        self._parse_comment(line, metadata)
                        continue
                    param = self._parse_parameter_line(line)
                    if param:
                        key, value = param
                        parameters[key] = value
                    else:
                        log.warning(f'{self._log_prefix} Linha inválida {line_num}: {line}')
            result = {'metadata': metadata, 'parameters': parameters, 'file_info': {'path': str(file_path), 'size': file_path.stat().st_size, 'modified': file_path.stat().st_mtime}}
            log.info(f'{self._log_prefix} Arquivo parseado: {len(parameters)} parâmetros')
            return result
        except Exception as e:
            log.error(f'{self._log_prefix} Erro ao parsear arquivo: {e}')
            return None

    def _parse_comment(self, line: str, metadata: Dict[str, Any]):
        line = line.lstrip('#').strip()
        if line.startswith('{') and '}' in line:
            metadata['device_info'] = line
        elif 'GenApi persistence file' in line:
            version_match = re.search('version (\\d+\\.\\d+\\.\\d+)', line)
            if version_match:
                metadata['genapi_version'] = version_match.group(1)
        elif 'Device =' in line:
            device_match = re.search('Device = (.+)', line)
            if device_match:
                metadata['device'] = device_match.group(1).strip()
        elif 'Product GUID =' in line:
            guid_match = re.search('Product GUID = ([A-F0-9-]+)', line)
            if guid_match:
                metadata['product_guid'] = guid_match.group(1)

    def _parse_parameter_line(self, line: str) -> Optional[tuple]:
        parts = line.split('\t')
        if len(parts) < 2:
            return None
        param_name = parts[0].strip()
        if len(parts) >= 3 and parts[1].startswith('{') and ('}' in parts[1]):
            selector = parts[1].strip('{}')
            value = parts[2].strip()
            param_key = f'{param_name}@{{{selector}}}'
            return (param_key, value)
        else:
            value = parts[1].strip()
            return (param_name, value)

    def create_pfs_content(self, parameters: Dict[str, Any], metadata: Optional[Dict[str, Any]]=None) -> str:
        lines = []
        lines.append('# {05D8C294-F295-4dfb-9D01-096BD04049F4}')
        lines.append('# GenApi persistence file (version 3.5.0)')
        if metadata:
            if 'device' in metadata:
                lines.append(f"# Device = {metadata['device']}")
            if 'product_guid' in metadata:
                lines.append(f"# Product GUID = {metadata['product_guid']}")
            if 'product_version_guid' in metadata:
                lines.append(f"# Product version GUID = {metadata['product_version_guid']}")
        lines.append('')
        for param_key, value in sorted(parameters.items()):
            if '@{' in param_key and param_key.endswith('}'):
                param_name, selector_part = param_key.split('@', 1)
                selector = selector_part.strip('{}')
                lines.append(f'{param_name}\t{{{selector}}}\t{value}')
            else:
                lines.append(f'{param_key}\t{value}')
        return '\n'.join(lines)

    def save_pfs_file(self, file_path: Path, parameters: Dict[str, Any], metadata: Optional[Dict[str, Any]]=None) -> bool:
        try:
            content = self.create_pfs_content(parameters, metadata)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            log.info(f'{self._log_prefix} Arquivo salvo: {file_path}')
            return True
        except Exception as e:
            log.error(f'{self._log_prefix} Erro ao salvar arquivo: {e}')
            return False

    def get_parameter_value(self, parsed_data: Dict[str, Any], param_name: str, selector: Optional[str]=None) -> Optional[str]:
        parameters = parsed_data.get('parameters', {})
        if selector:
            param_key = f'{param_name}@{{{selector}}}'
        else:
            param_key = param_name
        return parameters.get(param_key)

    def set_parameter_value(self, parsed_data: Dict[str, Any], param_name: str, value: str, selector: Optional[str]=None):
        parameters = parsed_data.setdefault('parameters', {})
        if selector:
            param_key = f'{param_name}@{{{selector}}}'
        else:
            param_key = param_name
        parameters[param_key] = value

    def get_all_parameters_by_name(self, parsed_data: Dict[str, Any], param_name: str) -> Dict[str, str]:
        parameters = parsed_data.get('parameters', {})
        result = {}
        for key, value in parameters.items():
            if key == param_name or key.startswith(f'{param_name}@{{'):
                if '@{' in key and key.endswith('}'):
                    selector = key.split('@', 1)[1]
                    result[selector] = value
                else:
                    result['default'] = value
        return result