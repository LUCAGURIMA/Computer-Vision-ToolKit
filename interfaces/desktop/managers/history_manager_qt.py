"""
HistoryManager Qt - Wrapper PyQt5 para HistoryManager do core.

Adiciona:
- Signals PyQt5 para comunicação UI
- Métodos agnósticos (apenas delegam ao core manager)

Tipo: Adapter Pattern
"""

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from pathlib import Path
from typing import Optional, Dict, Any

from core.managers import HistoryManager as CoreHistoryManager


class HistoryManagerQt(QObject):
    """
    Wrapper Qt para HistoryManager do core.
    
    Adiciona signals PyQt5 mas mantém lógica pura no core.
    
    Design:
    - Usa composition (não herança)
    - Cria uma instância do manager core
    - Delega todos os métodos
    - Adiciona signals para notificações
    """
    
    # Signals
    history_loaded = pyqtSignal()  # Emitido quando histórico carregado
    history_changed = pyqtSignal()  # Emitido quando histórico modificado
    error_occurred = pyqtSignal(str)  # Emitido em caso de erro
    
    def __init__(self, core, results_dir: Optional[Path] = None):
        """
        Inicializa o wrapper Qt.
        
        Args:
            core: Instância do SystemCore
            results_dir: Diretório de resultados (padrão: data/results)
        """
        super().__init__()
        
        # Cria manager core (lógica pura)
        self.manager = CoreHistoryManager(core, results_dir)
        
        # Registra listener para notificações do core
        if hasattr(core, 'register_callback'):
            core.register_callback("history_loaded", self._on_history_loaded)
            core.register_callback("history_modified", self._on_history_modified)
            core.register_callback("history_error", self._on_history_error)
    
    # Métodos que delegam ao core manager
    
    def load_history(self):
        """Carrega histórico e emite signal"""
        try:
            result = self.manager.load_history()
            self.history_loaded.emit()
            return result
        except Exception as e:
            self.error_occurred.emit(str(e))
            return []
    
    def initialize(self) -> bool:
        """Inicializa o manager"""
        try:
            return self.manager.initialize()
        except Exception as e:
            self.error_occurred.emit(str(e))
            return False
    
    def cleanup(self) -> None:
        """Limpa recursos"""
        self.manager.cleanup()
    
    def get_history_item(self, index: int) -> Optional[Dict]:
        """Retorna item por índice"""
        return self.manager.get_history_item(index)
    
    def get_history_by_timestamp(self, timestamp: str) -> Optional[Dict]:
        """Retorna item por timestamp"""
        return self.manager.get_history_by_timestamp(timestamp)
    
    def get_history_count(self) -> int:
        """Retorna quantidade de itens"""
        return self.manager.get_history_count()
    
    def view_history_item(self, item_index: int) -> Optional[str]:
        """Retorna item formatado para visualização"""
        return self.manager.view_history_item(item_index)
    
    def export_to_csv(self, output_path: Path) -> bool:
        """Exporta para CSV"""
        try:
            success = self.manager.export_to_csv(output_path)
            if success:
                self.history_changed.emit()
            return success
        except Exception as e:
            self.error_occurred.emit(str(e))
            return False
    
    def delete_history_item(self, timestamp: str) -> bool:
        """Deleta item"""
        try:
            success = self.manager.delete_history_item(timestamp)
            if success:
                self.history_changed.emit()
            return success
        except Exception as e:
            self.error_occurred.emit(str(e))
            return False
    
    def clear_all_history(self) -> bool:
        """Limpa todo o histórico"""
        try:
            success = self.manager.clear_all_history()
            if success:
                self.history_changed.emit()
            return success
        except Exception as e:
            self.error_occurred.emit(str(e))
            return False
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas"""
        return self.manager.get_summary_stats()
    
    # Slots para callbacks do core
    
    @pyqtSlot()
    def _on_history_loaded(self):
        """Callback quando histórico carregado"""
        self.history_loaded.emit()
    
    @pyqtSlot()
    def _on_history_modified(self):
        """Callback quando histórico modificado"""
        self.history_changed.emit()
    
    @pyqtSlot(str)
    def _on_history_error(self, error: str):
        """Callback em caso de erro"""
        self.error_occurred.emit(error)
