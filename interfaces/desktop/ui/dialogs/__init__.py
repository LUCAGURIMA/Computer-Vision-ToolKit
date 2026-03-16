"""Dialog classes for desktop interface."""

from .crop_dialog import CropDialog
from .history_image_dialog import HistoryImageDialog
from .detection_dialog import DetectionDialog
from .create_profile_dialog import CreateProfileDialog
from .streaming_popup_window import StreamingPopupWindow

__all__ = [
    'CropDialog',
    'HistoryImageDialog',
    'DetectionDialog',
    'CreateProfileDialog',
    'StreamingPopupWindow',
]
