"""
Managers para desktop UI - separam lógica de negócio da UI
"""

from .capture_manager import CaptureManager
from .inspection_manager import InspectionManager
from .history_manager import HistoryManager

__all__ = [
    "CaptureManager",
    "InspectionManager",
    "HistoryManager",
]
