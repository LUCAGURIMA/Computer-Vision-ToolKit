"""Panel for displaying inspection results with images."""

from typing import Optional, Dict
import cv2
import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from core.utils.logger import log


class InspectionResultsPanel(QWidget):
    """Panel for displaying inspection results with annotated images.
    
    Shows real-time inspection results with status indicators.
    """

    def __init__(self, parent=None):
        """Initialize inspection results panel.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.image: Optional[np.ndarray] = None
        self.result: Optional[Dict] = None
        self.inspection_type: Optional[str] = None
        self.annotated_image: Optional[np.ndarray] = None
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Info label
        self.info_label = QLabel('Aguardando resultado da inspeção...')
        self.info_label.setStyleSheet(
            'font-weight: bold; font-size: 16px; padding: 8px; '
            'background-color: #2a2a2a;'
        )
        self.info_label.setMaximumHeight(30)
        layout.addWidget(self.info_label, 0)
        
        # Scroll area for image
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(
            'QScrollArea { border: none; background-color: #1a1a1a; } '
            'QScrollBar:vertical { width: 12px; } '
            'QScrollBar:horizontal { height: 12px; }'
        )
        
        self.image_container = QWidget()
        self.image_container.setStyleSheet('background-color: #1a1a1a;')
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        self.image_label = QLabel('Imagem aparecerá aqui')
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet(
            'border: none; background-color: #1a1a1a;'
        )
        self.image_label.setMinimumHeight(300)
        self.image_label.setMinimumWidth(300)
        container_layout.addWidget(self.image_label, 1)
        
        self.image_container.setLayout(container_layout)
        self.scroll_area.setWidget(self.image_container)
        layout.addWidget(self.scroll_area, 1)
        
        self.setLayout(layout)
        self.setMinimumHeight(200)

    def display_results(
        self,
        image: np.ndarray,
        result: Dict,
        inspection_type: str
    ):
        """Display inspection results.
        
        Args:
            image: Original image for inspection
            result: Detection/inference results
            inspection_type: Type of inspection ('segmentation' or 'classification')
        """
        self.image = image.copy()
        self.result = result
        self.inspection_type = inspection_type
        self.annotated_image = self._draw_detections()
        self._display_image()
        self._update_result_info()

    def clear_results(self):
        """Clear displayed results."""
        self.image = None
        self.result = None
        self.inspection_type = None
        self.annotated_image = None
        self.image_label.setText('Imagem aparecerá aqui')
        self.image_label.setPixmap(QPixmap())
        self.info_label.setText('Aguardando resultado da inspeção...')

    def _display_image(self):
        """Display the annotated image."""
        if self.annotated_image is None:
            return
        
        image = self.annotated_image
        if len(image.shape) == 3 and image.shape[2] == 3:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = image
        
        h, w = image_rgb.shape[:2]
        if len(image_rgb.shape) == 3:
            bytes_per_line = 3 * w
            from PyQt5.QtGui import QImage
            qimage = QImage(
                image_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888
            )
        else:
            bytes_per_line = w
            from PyQt5.QtGui import QImage
            qimage = QImage(
                image_rgb.data, w, h, bytes_per_line, QImage.Format_Grayscale8
            )
        
        pixmap = QPixmap.fromImage(qimage)
        viewport_size = self.scroll_area.viewport().size()
        available_width = viewport_size.width()
        available_height = viewport_size.height()
        
        if available_width <= 1 or available_height <= 1:
            scale = min(800 / w, 600 / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            scaled_pixmap = pixmap.scaledToWidth(
                new_w, Qt.SmoothTransformation
            )
        else:
            aspect_ratio = w / h
            viewport_aspect = available_width / available_height
            if aspect_ratio > viewport_aspect:
                new_w = available_width
                new_h = int(available_width / aspect_ratio)
            else:
                new_h = available_height
                new_w = int(available_height * aspect_ratio)
            scaled_pixmap = pixmap.scaled(
                new_w, new_h, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        
        self.image_label.setPixmap(scaled_pixmap)

    def _update_result_info(self):
        """Update result info label with status."""
        if self.inspection_type == 'segmentation':
            total_defects = self.result.get('total_defects', 0)
            has_defects = self.result.get('has_defects', False)
            
            if has_defects:
                info_text = f' {total_defects} DEFEITO(S) ENCONTRADO(S)'
                self.info_label.setStyleSheet(
                    'color: orange; font-weight: bold; font-size: 16px; '
                    'padding: 10px;'
                )
            else:
                info_text = ' NENHUM DEFEITO ENCONTRADO'
                self.info_label.setStyleSheet(
                    'color: green; font-weight: bold; font-size: 16px; '
                    'padding: 10px;'
                )
        
        elif self.inspection_type == 'classification':
            status = self.result.get('status', 'unknown')
            defects_detected = self.result.get('defects_detected', False)
            
            if status == 'indeterminado':
                info_text = ' INDETERMINADO'
                self.info_label.setStyleSheet(
                    'color: orange; font-weight: bold; font-size: 16px; '
                    'padding: 10px;'
                )
            elif defects_detected:
                info_text = ' FRUTA RUIM'
                self.info_label.setStyleSheet(
                    'color: red; font-weight: bold; font-size: 16px; '
                    'padding: 10px;'
                )
            else:
                info_text = ' FRUTA BOA'
                self.info_label.setStyleSheet(
                    'color: green; font-weight: bold; font-size: 16px; '
                    'padding: 10px;'
                )
        
        self.info_label.setText(info_text)

    def _draw_detections(self) -> np.ndarray:
        """Draw detection boxes and labels on image."""
        annotated = self.image.copy()
        
        if self.inspection_type == 'segmentation':
            defects = self.result.get('defects', [])
            colors = [
                (0, 255, 0), (255, 0, 0), (0, 255, 255),
                (255, 0, 255), (255, 127, 0)
            ]
            
            for i, defect in enumerate(defects):
                bbox = defect.get('bbox', [])
                if len(bbox) >= 4:
                    x1, y1, x2, y2 = map(int, bbox[:4])
                    confidence = defect.get('confidence', 0)
                    class_name = defect.get('class_name', 'Desconhecido')
                    color = colors[i % len(colors)]
                    
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                    
                    label = f'{class_name}: {confidence:.2%}'
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    font_scale = 0.6
                    thickness = 1
                    text_size = cv2.getTextSize(
                        label, font, font_scale, thickness
                    )[0]
                    cv2.rectangle(
                        annotated,
                        (x1, y1 - text_size[1] - 5),
                        (x1 + text_size[0], y1),
                        color,
                        -1
                    )
                    cv2.putText(
                        annotated, label, (x1, y1 - 5),
                        font, font_scale, (255, 255, 255), thickness
                    )
        
        elif self.inspection_type == 'classification':
            h, w = annotated.shape[:2]
            status = self.result.get('status', 'unknown')
            
            if status == 'indeterminado':
                color = (0, 127, 255)
                label = 'INDETERMINADO'
            elif self.result.get('defects_detected'):
                color = (0, 0, 255)
                label = 'FRUTA RUIM'
            else:
                color = (0, 255, 0)
                label = 'FRUTA BOA'
            
            cv2.rectangle(annotated, (10, 10), (w - 10, h - 10), color, 3)
            
            defects_info = self.result.get('defects_info', [])
            if defects_info:
                defect = defects_info[0]
                confidence = defect.get('confidence', 0)
                label_text = f'{label} ({confidence:.1%})'
            else:
                label_text = label
            
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 1.5
            thickness = 2
            text_size = cv2.getTextSize(
                label_text, font, font_scale, thickness
            )[0]
            cv2.rectangle(
                annotated,
                (20, 30),
                (20 + text_size[0], 30 + text_size[1] + 10),
                color,
                -1
            )
            cv2.putText(
                annotated, label_text, (20, 50),
                font, font_scale, (255, 255, 255), thickness
            )
        
        return annotated
