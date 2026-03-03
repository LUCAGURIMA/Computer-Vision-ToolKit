from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from pathlib import Path
from typing import Optional, Dict, Any
from core.managers import HistoryManager as CoreHistoryManager

class HistoryManagerQt(QObject):
    history_loaded = pyqtSignal()
    history_changed = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, core, results_dir: Optional[Path]=None):
        super().__init__()
        self.manager = CoreHistoryManager(core, results_dir)
        if hasattr(core, 'register_callback'):
            core.register_callback('history_loaded', self._on_history_loaded)
            core.register_callback('history_modified', self._on_history_modified)
            core.register_callback('history_error', self._on_history_error)

    def load_history(self):
        try:
            result = self.manager.load_history()
            self.history_loaded.emit()
            return result
        except Exception as e:
            self.error_occurred.emit(str(e))
            return []

    def initialize(self) -> bool:
        try:
            return self.manager.initialize()
        except Exception as e:
            self.error_occurred.emit(str(e))
            return False

    def cleanup(self) -> None:
        self.manager.cleanup()

    def get_history_item(self, index: int) -> Optional[Dict]:
        return self.manager.get_history_item(index)

    def get_history_by_timestamp(self, timestamp: str) -> Optional[Dict]:
        return self.manager.get_history_by_timestamp(timestamp)

    def get_history_count(self) -> int:
        return self.manager.get_history_count()

    def view_history_item(self, item_index: int) -> Optional[str]:
        return self.manager.view_history_item(item_index)

    def export_to_csv(self, output_path: Path) -> bool:
        try:
            success = self.manager.export_to_csv(output_path)
            if success:
                self.history_changed.emit()
            return success
        except Exception as e:
            self.error_occurred.emit(str(e))
            return False

    def delete_history_item(self, timestamp: str) -> bool:
        try:
            success = self.manager.delete_history_item(timestamp)
            if success:
                self.history_changed.emit()
            return success
        except Exception as e:
            self.error_occurred.emit(str(e))
            return False

    def clear_all_history(self) -> bool:
        try:
            success = self.manager.clear_all_history()
            if success:
                self.history_changed.emit()
            return success
        except Exception as e:
            self.error_occurred.emit(str(e))
            return False

    def get_summary_stats(self) -> Dict[str, Any]:
        return self.manager.get_summary_stats()

    @pyqtSlot()
    def _on_history_loaded(self):
        self.history_loaded.emit()

    @pyqtSlot()
    def _on_history_modified(self):
        self.history_changed.emit()

    @pyqtSlot(str)
    def _on_history_error(self, error: str):
        self.error_occurred.emit(error)