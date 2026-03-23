"""UI module initialization - aggregates all UI components."""

from .widgets import BaseWidget
from .dialogs import (
    CropDialog,
    HistoryImageDialog,
    DetectionDialog,
    CreateProfileDialog,
    StreamingPopupWindow,
)
from .panels import InspectionResultsPanel
from .builders import (
    build_capture_tab,
    build_inspection_tab,
    build_results_tab,
    build_pfs_tab,
    build_settings_tab,
)
from .hybrid_inspection_widget import HybridInspectionTab

__all__ = [
    'BaseWidget',
    'CropDialog',
    'HistoryImageDialog',
    'DetectionDialog',
    'CreateProfileDialog',
    'StreamingPopupWindow',
    'InspectionResultsPanel',
    'HybridInspectionTab',
    'build_capture_tab',
    'build_inspection_tab',
    'build_results_tab',
    'build_pfs_tab',
    'build_settings_tab',
]
