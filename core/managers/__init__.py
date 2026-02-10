"""
Managers do core do sistema.

Exporta os managers agnósticos de UI para reutilização em:
- Desktop (PyQt5)
- Web (FastAPI)
- CLI (scripts)

Uso:
    from core.managers import CaptureManager, InspectionManager, HistoryManager
"""

from .base_manager import BaseManager
from .history_manager import HistoryManager
from .capture_manager import CaptureManager

__all__ = [
    'BaseManager',
    'HistoryManager',
    'CaptureManager',
]

# Imports dos managers serão adicionados à medida que forem criados
# from .inspection_manager import InspectionManager
