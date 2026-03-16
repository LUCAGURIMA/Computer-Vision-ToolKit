"""Streaming popup window for real-time camera preview."""

from typing import TYPE_CHECKING, Optional
import cv2
import numpy as np
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QMessageBox
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal
from core.utils.logger import log
from ...threads import StreamingThread

if TYPE_CHECKING:
    from core.system_core import SystemCore


class StreamingPopupWindow(QDialog):
    """Popup window for streaming camera preview.
    
    Signals:
        popup_closed: Emitted when window is closed
    """
    
    popup_closed = pyqtSignal()

    def __init__(self, core: 'SystemCore', parent=None):
        """Initialize streaming popup.
        
        Args:
            core: SystemCore instance for image capture
            parent: Parent widget
        """
        super().__init__(parent)
        self.core = core
        self.streaming_thread: Optional[StreamingThread] = None
        
        self.setWindowTitle(' Streaming de Câmera')
        self.setGeometry(100, 100, 800, 600)
        self.setModal(False)
        
        layout = QVBoxLayout()
        
        self.image_label = QLabel('Iniciando streaming...')
        self.image_label.setMinimumSize(640, 480)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet(
            'border: 2px solid #555; background-color: #1a1a1a;'
        )
        layout.addWidget(self.image_label)
        
        self.info_label = QLabel('FPS: -- | Resolução: --')
        layout.addWidget(self.info_label)
        
        close_btn = QPushButton(' Fechar Streaming')
        close_btn.clicked.connect(self.stop_streaming)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
        self.start_streaming()

    def start_streaming(self):
        """Start streaming thread."""
        self.streaming_thread = StreamingThread(self.core, target_fps=30)
        self.streaming_thread.frame_ready.connect(self._on_streaming_frame)
        self.streaming_thread.fps_info.connect(self._on_streaming_fps)
        self.streaming_thread.error_occurred.connect(self._on_streaming_error)
        self.streaming_thread.start()

    @pyqtSlot(object)
    def _on_streaming_frame(self, frame: np.ndarray):
        """Handle incoming frame from streaming thread."""
        try:
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                frame_rgb = frame
            
            h, w = frame_rgb.shape[:2]
            bytes_per_line = 3 * w if len(frame_rgb.shape) == 3 else w
            
            qimage = QImage(
                frame_rgb.data, w, h, bytes_per_line,
                QImage.Format_RGB888 if len(frame_rgb.shape) == 3
                else QImage.Format_Indexed8
            )
            pixmap = QPixmap.fromImage(qimage)
            label_size = self.image_label.size()
            scaled_pixmap = pixmap.scaled(
                label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
        except Exception as e:
            log.debug(f'[StreamingPopupWindow] Error displaying frame: {e}')

    @pyqtSlot(float)
    def _on_streaming_fps(self, fps: float):
        """Handle FPS update from streaming thread."""
        self.info_label.setText(f'FPS: {fps:.1f} | Resolução: --')

    @pyqtSlot(str)
    def _on_streaming_error(self, error_msg: str):
        """Handle streaming error."""
        QMessageBox.warning(
            self, 'Erro no Streaming', f'Erro: {error_msg}'
        )
        self.close()

    def stop_streaming(self):
        """Stop streaming and close window."""
        if self.streaming_thread:
            self.streaming_thread.stop()
            self.streaming_thread = None
        self.close()

    def showEvent(self, event):
        """Handle window show event."""
        log.info('[StreamingPopupWindow] Window show event triggered')
        super().showEvent(event)

    def closeEvent(self, event):
        """Handle window close event."""
        # Para a thread antes de fechar
        if self.streaming_thread:
            self.streaming_thread.stop()
            self.streaming_thread = None
        log.info('[StreamingPopupWindow] Window close event triggered')
        self.popup_closed.emit()
        super().closeEvent(event)
