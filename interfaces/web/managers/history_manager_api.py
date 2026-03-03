from typing import Dict, Any, List
from pathlib import Path
from core.managers import HistoryManager as CoreHistoryManager

class HistoryManagerAPI:

    def __init__(self, core, results_dir: str=None):
        results_path = Path(results_dir) if results_dir else None
        self.manager = CoreHistoryManager(core, results_path)

    def initialize(self) -> bool:
        return self.manager.initialize()

    def cleanup(self) -> None:
        self.manager.cleanup()

    async def get_all_history(self) -> Dict[str, Any]:
        try:
            self.manager.load_history()
            return {'success': True, 'count': self.manager.get_history_count(), 'data': self.manager.loaded_history}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def get_history_item(self, index: int) -> Dict[str, Any]:
        try:
            item = self.manager.get_history_item(index)
            if item:
                return {'success': True, 'data': item}
            else:
                return {'success': False, 'error': f'Item {index} não encontrado'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def get_history_by_timestamp(self, timestamp: str) -> Dict[str, Any]:
        try:
            item = self.manager.get_history_by_timestamp(timestamp)
            if item:
                return {'success': True, 'data': item}
            else:
                return {'success': False, 'error': f'Timestamp {timestamp} não encontrado'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def get_history_count(self) -> Dict[str, Any]:
        try:
            count = self.manager.get_history_count()
            return {'success': True, 'count': count}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def get_summary_stats(self) -> Dict[str, Any]:
        try:
            stats = self.manager.get_summary_stats()
            return {'success': True, 'stats': stats}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def view_history_item(self, index: int) -> Dict[str, Any]:
        try:
            view = self.manager.view_history_item(index)
            if view:
                return {'success': True, 'formatted': view}
            else:
                return {'success': False, 'error': f'Item {index} não encontrado'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def export_to_csv(self, output_filename: str) -> Dict[str, Any]:
        try:
            output_path = Path('data') / 'exports' / output_filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            success = self.manager.export_to_csv(output_path)
            if success:
                return {'success': True, 'path': str(output_path), 'filename': output_filename}
            else:
                return {'success': False, 'error': 'Histórico vazio para exportar'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def delete_history_item(self, timestamp: str) -> Dict[str, Any]:
        try:
            success = self.manager.delete_history_item(timestamp)
            if success:
                return {'success': True, 'deleted': timestamp}
            else:
                return {'success': False, 'error': f'Item {timestamp} não encontrado'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def clear_all_history(self) -> Dict[str, Any]:
        try:
            success = self.manager.clear_all_history()
            if success:
                return {'success': True, 'message': 'Todo o histórico foi permanentemente deletado'}
            else:
                return {'success': False, 'error': 'Falha ao limpar histórico'}
        except Exception as e:
            return {'success': False, 'error': str(e)}