"""Dialog for selecting crop region on an image."""

from typing import Optional, List
import cv2
import numpy as np
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QRubberBand
)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QRect, QSize


class CropDialog(QDialog):
    """Dialog for interactive crop region selection.
    
    Allows user to drag a rectangle on the image to select crop area.
    """

    def __init__(self, image: np.ndarray, parent=None):
        """Initialize crop dialog.
        
        Args:
            image: Image to select crop region from
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle('Selecionar Crop')
        self.image = image
        self.bbox: Optional[List[int]] = None
        
        # Convert image to display format
        if len(image.shape) == 3 and image.shape[2] == 3:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            h, w, ch = image_rgb.shape
            bytes_per_line = ch * w
            qimage = QImage(image_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        else:
            image_rgb = image
            h, w = image_rgb.shape[:2]
            bytes_per_line = w
            qimage = QImage(image_rgb.data, w, h, bytes_per_line, QImage.Format_Indexed8)
        
        pixmap = QPixmap.fromImage(qimage)
        max_display = QSize(min(w, 800), min(h, 600))
        display_pixmap = pixmap.scaled(
            max_display, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        
        # Create label with image
        self.label = QLabel()
        self.label.setPixmap(display_pixmap)
        self.label.setFixedSize(display_pixmap.size())
        self.label.setAlignment(Qt.AlignCenter)
        
        # Create rubber band for selection rectangle
        self.rubber = QRubberBand(QRubberBand.Rectangle, self.label)
        self.origin: Optional[QRect] = None
        
        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton('OK')
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton('Cancelar')
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
        # Connect mouse events
        self.label.mousePressEvent = self._mouse_press
        self.label.mouseMoveEvent = self._mouse_move
        self.label.mouseReleaseEvent = self._mouse_release

    def _mouse_press(self, event):
        """Handle mouse press to start crop selection."""
        self.origin = event.pos()
        self.rubber.setGeometry(QRect(self.origin, QSize()))
        self.rubber.show()

    def _mouse_move(self, event):
        """Handle mouse move to update crop selection."""
        if self.origin:
            rect = QRect(self.origin, event.pos()).normalized()
            self.rubber.setGeometry(rect)

    def _mouse_release(self, event):
        """Handle mouse release to finalize crop selection."""
        if self.origin:
            rect = self.rubber.geometry()
            display_pixmap = self.label.pixmap()
            if display_pixmap is None:
                return
            
            # Scale from display coordinates to original image coordinates
            dp_w = display_pixmap.width()
            dp_h = display_pixmap.height()
            orig_h, orig_w = self.image.shape[:2]
            sx = orig_w / dp_w
            sy = orig_h / dp_h
            
            x1 = int(rect.left() * sx)
            y1 = int(rect.top() * sy)
            x2 = int(rect.right() * sx)
            y2 = int(rect.bottom() * sy)
            
            # Ensure coordinates are within bounds
            x1 = max(0, min(orig_w - 1, x1))
            x2 = max(0, min(orig_w, x2))
            y1 = max(0, min(orig_h - 1, y1))
            y2 = max(0, min(orig_h, y2))
            
            if x2 > x1 and y2 > y1:
                self.bbox = [x1, y1, x2, y2]
            
            self.origin = None
            self.rubber.hide()

    def get_bbox(self) -> Optional[List[int]]:
        """Get the selected bounding box.
        
        Returns:
            [x1, y1, x2, y2] or None if cancelled
        """
        return self.bbox
