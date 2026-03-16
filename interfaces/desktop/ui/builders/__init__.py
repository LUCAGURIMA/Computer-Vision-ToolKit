"""UI Tab builders for modular tab creation."""

from .capture_tab_builder import build_capture_tab
from .inspection_tab_builder import build_inspection_tab
from .results_tab_builder import build_results_tab
from .pfs_tab_builder import build_pfs_tab
from .settings_tab_builder import build_settings_tab

__all__ = [
    'build_capture_tab',
    'build_inspection_tab',
    'build_results_tab',
    'build_pfs_tab',
    'build_settings_tab',
]
