import sys
import json
from datetime import datetime
from typing import Dict, Any
from typing import Optional
from pathlib import Path
from queue import Queue
import shutil
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextEdit, QTabWidget, QGroupBox, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QSystemTrayIcon, QMenu, QAction, QStyle, QDialog, QRubberBand, QLineEdit, QFileDialog, QInputDialog, QScrollArea, QSizePolicy
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QTimer, QRect, QSize
from PyQt5.QtGui import QImage, QPixmap, QIcon, QFont
import cv2
import numpy as np
import signal
import time
from core.system_core import SystemCore
from core.utils.logger import log
from core.camera.basler_profile_manager import BaslerProfileManager
from config import DESKTOP_CONFIG, ASSETS_DIR, get_available_models
from .managers.capture_manager_qt import CaptureManagerQt
from .managers import InspectionManager, HistoryManager

class CaptureThread(QThread):
    image_captured = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, core: SystemCore):
        super().__init__()
        self.core = core

    def run(self):
        try:
            result = self.core.capture_image()
            if result and result.get('success'):
                self.image_captured.emit(result)
            else:
                self.error_occurred.emit('Falha na captura')
        except Exception as e:
            self.error_occurred.emit(str(e))

class StreamingThread(QThread):
    frame_ready = pyqtSignal(np.ndarray)
    error_occurred = pyqtSignal(str)
    fps_info = pyqtSignal(float)

    def __init__(self, core: SystemCore, target_fps: int=30):
        super().__init__()
        self.core = core
        self.target_fps = target_fps
        self.frame_interval = 1.0 / target_fps
        self.running = True
        self.frame_count = 0
        self.start_time = time.time()

    def run(self):
        try:
            while self.running:
                loop_start = time.time()
                try:
                    result = self.core.capture_image()
                    if result and result.get('success'):
                        frame = result.get('image')
                        if frame is not None:
                            self.frame_ready.emit(frame)
                            self.frame_count += 1
                except Exception as e:
                    log.debug(f'Erro ao capturar frame: {e}')
                    continue
                elapsed = time.time() - loop_start
                sleep_time = max(0, self.frame_interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                if self.frame_count % 30 == 0:
                    current_fps = 30 / (time.time() - self.start_time + 0.001)
                    self.fps_info.emit(current_fps)
                    self.frame_count = 0
                    self.start_time = time.time()
        except Exception as e:
            self.error_occurred.emit(str(e))

    def stop(self):
        self.running = False
        self.wait()

class CropDialog(QDialog):

    def __init__(self, image: np.ndarray, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Selecionar Crop')
        self.image = image
        self.bbox = None
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
        display_pixmap = pixmap.scaled(max_display, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.label = QLabel()
        self.label.setPixmap(display_pixmap)
        self.label.setFixedSize(display_pixmap.size())
        self.label.setAlignment(Qt.AlignCenter)
        self.rubber = QRubberBand(QRubberBand.Rectangle, self.label)
        self.origin = None
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
        self.label.mousePressEvent = self._mouse_press
        self.label.mouseMoveEvent = self._mouse_move
        self.label.mouseReleaseEvent = self._mouse_release

    def _mouse_press(self, event):
        self.origin = event.pos()
        self.rubber.setGeometry(QRect(self.origin, QSize()))
        self.rubber.show()

    def _mouse_move(self, event):
        if self.origin:
            rect = QRect(self.origin, event.pos()).normalized()
            self.rubber.setGeometry(rect)

    def _mouse_release(self, event):
        if self.origin:
            rect = self.rubber.geometry()
            display_pixmap = self.label.pixmap()
            if display_pixmap is None:
                return
            dp_w = display_pixmap.width()
            dp_h = display_pixmap.height()
            orig_h, orig_w = self.image.shape[:2]
            sx = orig_w / dp_w
            sy = orig_h / dp_h
            x1 = int(rect.left() * sx)
            y1 = int(rect.top() * sy)
            x2 = int(rect.right() * sx)
            y2 = int(rect.bottom() * sy)
            x1 = max(0, min(orig_w - 1, x1))
            x2 = max(0, min(orig_w, x2))
            y1 = max(0, min(orig_h - 1, y1))
            y2 = max(0, min(orig_h, y2))
            if x2 > x1 and y2 > y1:
                self.bbox = [x1, y1, x2, y2]
            self.origin = None
            self.rubber.hide()

class HistoryImageDialog(QDialog):

    def __init__(self, folder: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'Visualizar histórico - {folder.name}')
        layout = QVBoxLayout()

        def add_image(path: Path, title: str):
            if path.exists():
                label = QLabel(title)
                label.setAlignment(Qt.AlignCenter)
                layout.addWidget(label)
                pix = QPixmap(str(path))
                img_lbl = QLabel()
                img_lbl.setAlignment(Qt.AlignCenter)
                img_lbl.setPixmap(pix)
                scroll = QScrollArea()
                scroll.setWidgetResizable(True)
                scroll.setWidget(img_lbl)
                layout.addWidget(scroll)
        annotated_path = folder / 'annotated.jpg'
        image_path = folder / 'image.jpg'
        if annotated_path.exists():
            add_image(annotated_path, 'Anotada')
        elif image_path.exists():
            add_image(image_path, 'Imagem')
        else:
            layout.addWidget(QLabel('Nenhuma imagem disponível.'))
        self.setLayout(layout)

class InspectionThread(QThread):
    inspection_completed = pyqtSignal(dict, str)
    error_occurred = pyqtSignal(str)

    def __init__(self, core: SystemCore, inspection_type: str, image: np.ndarray=None, model_name: str=None):
        super().__init__()
        self.core = core
        self.inspection_type = inspection_type
        self.image = image
        self.model_name = model_name

    def run(self):
        try:
            if self.inspection_type == 'segmentation':
                result = self.core.perform_segmentation(self.image, model_name=self.model_name)
            elif self.inspection_type == 'classification':
                result = self.core.perform_classification(self.image, model_name=self.model_name)
            else:
                raise ValueError(f'Tipo de inspeção inválido: {self.inspection_type}')
            self.inspection_completed.emit(result, self.inspection_type)
        except Exception as e:
            log.error(f'Exception in InspectionThread: {e}', exc_info=True)
            self.error_occurred.emit(repr(e))

class InspectionResultsPanel(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = None
        self.result = None
        self.inspection_type = None
        self.annotated_image = None
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.info_label = QLabel('Aguardando resultado da inspeção...')
        self.info_label.setStyleSheet('font-weight: bold; font-size: 12px; padding: 8px; background-color: #2a2a2a;')
        self.info_label.setMaximumHeight(30)
        layout.addWidget(self.info_label, 0)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet('QScrollArea { border: none; background-color: #1a1a1a; } QScrollBar:vertical { width: 12px; } QScrollBar:horizontal { height: 12px; }')
        self.image_container = QWidget()
        self.image_container.setStyleSheet('background-color: #1a1a1a;')
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        self.image_label = QLabel('Imagem aparecerá aqui')
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet('border: none; background-color: #1a1a1a;')
        self.image_label.setMinimumHeight(300)
        self.image_label.setMinimumWidth(300)
        container_layout.addWidget(self.image_label, 1)
        self.image_container.setLayout(container_layout)
        self.scroll_area.setWidget(self.image_container)
        layout.addWidget(self.scroll_area, 1)
        self.setLayout(layout)
        self.setMinimumHeight(200)

    def display_results(self, image: np.ndarray, result: dict, inspection_type: str):
        self.image = image.copy()
        self.result = result
        self.inspection_type = inspection_type
        self.annotated_image = self._draw_detections()
        self._display_image()
        self._update_result_info()

    def clear_results(self):
        self.image = None
        self.result = None
        self.inspection_type = None
        self.annotated_image = None
        self.image_label.setText('Imagem aparecerá aqui')
        self.image_label.setPixmap(QPixmap())
        self.info_label.setText('Aguardando resultado da inspeção...')

    def _display_image(self):
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
            qimage = QImage(image_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        else:
            bytes_per_line = w
            qimage = QImage(image_rgb.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
        pixmap = QPixmap.fromImage(qimage)
        viewport_size = self.scroll_area.viewport().size()
        available_width = viewport_size.width()
        available_height = viewport_size.height()
        if available_width <= 1 or available_height <= 1:
            scale = min(800 / w, 600 / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            scaled_pixmap = pixmap.scaledToWidth(new_w, Qt.SmoothTransformation)
        else:
            aspect_ratio = w / h
            viewport_aspect = available_width / available_height
            if aspect_ratio > viewport_aspect:
                new_w = available_width
                new_h = int(available_width / aspect_ratio)
            else:
                new_h = available_height
                new_w = int(available_height * aspect_ratio)
            scaled_pixmap = pixmap.scaled(new_w, new_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)

    def _update_result_info(self):
        if self.inspection_type == 'segmentation':
            total_defects = self.result.get('total_defects', 0)
            has_defects = self.result.get('has_defects', False)
            if has_defects:
                info_text = f' {total_defects} DEFEITO(S) ENCONTRADO(S)'
                self.info_label.setStyleSheet('color: orange; font-weight: bold; font-size: 12px; padding: 10px;')
            else:
                info_text = ' NENHUM DEFEITO ENCONTRADO'
                self.info_label.setStyleSheet('color: green; font-weight: bold; font-size: 12px; padding: 10px;')
        elif self.inspection_type == 'classification':
            status = self.result.get('status', 'unknown')
            defects_detected = self.result.get('defects_detected', False)
            if status == 'indeterminado':
                info_text = ' INDETERMINADO'
                self.info_label.setStyleSheet('color: orange; font-weight: bold; font-size: 12px; padding: 10px;')
            elif defects_detected:
                info_text = ' FRUTA RUIM'
                self.info_label.setStyleSheet('color: red; font-weight: bold; font-size: 12px; padding: 10px;')
            else:
                info_text = ' FRUTA BOA'
                self.info_label.setStyleSheet('color: green; font-weight: bold; font-size: 12px; padding: 10px;')
        self.info_label.setText(info_text)

    def _draw_detections(self) -> np.ndarray:
        annotated = self.image.copy()
        if self.inspection_type == 'segmentation':
            defects = self.result.get('defects', [])
            colors = [(0, 255, 0), (255, 0, 0), (0, 255, 255), (255, 0, 255), (255, 127, 0)]
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
                    text_size = cv2.getTextSize(label, font, font_scale, thickness)[0]
                    cv2.rectangle(annotated, (x1, y1 - text_size[1] - 5), (x1 + text_size[0], y1), color, -1)
                    cv2.putText(annotated, label, (x1, y1 - 5), font, font_scale, (255, 255, 255), thickness)
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
            text_size = cv2.getTextSize(label_text, font, font_scale, thickness)[0]
            cv2.rectangle(annotated, (20, 30), (20 + text_size[0], 30 + text_size[1] + 10), color, -1)
            cv2.putText(annotated, label_text, (20, 50), font, font_scale, (255, 255, 255), thickness)
        return annotated

    def _numpy_to_pixmap(self, image: np.ndarray) -> QPixmap:
        if len(image.shape) == 3 and image.shape[2] == 3:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = image
        h, w = image_rgb.shape[:2]
        if len(image_rgb.shape) == 3:
            bytes_per_line = 3 * w
            qimage = QImage(image_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        else:
            bytes_per_line = w
            qimage = QImage(image_rgb.data, w, h, bytes_per_line, QImage.Format_Indexed8)
        return QPixmap.fromImage(qimage)

class DetectionDialog(QDialog):

    def __init__(self, image: np.ndarray, result: dict, inspection_type: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Resultados da Inspeção')
        self.setGeometry(100, 100, 1000, 800)
        self.image = image.copy()
        self.result = result
        self.inspection_type = inspection_type
        self.annotated_image = self._draw_detections()
        layout = QVBoxLayout()
        info_layout = QHBoxLayout()
        self._add_result_info(info_layout)
        layout.addLayout(info_layout)
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignCenter)
        pixmap = self._numpy_to_pixmap(self.annotated_image)
        image_label.setPixmap(pixmap.scaled(900, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(image_label)
        btn_layout = QHBoxLayout()
        close_btn = QPushButton('Fechar')
        close_btn.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _draw_detections(self) -> np.ndarray:
        annotated = self.image.copy()
        if self.inspection_type == 'segmentation':
            defects = self.result.get('defects', [])
            colors = [(0, 255, 0), (255, 0, 0), (0, 255, 255), (255, 0, 255), (255, 127, 0)]
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
                    text_size = cv2.getTextSize(label, font, font_scale, thickness)[0]
                    cv2.rectangle(annotated, (x1, y1 - text_size[1] - 5), (x1 + text_size[0], y1), color, -1)
                    cv2.putText(annotated, label, (x1, y1 - 5), font, font_scale, (255, 255, 255), thickness)
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
            text_size = cv2.getTextSize(label_text, font, font_scale, thickness)[0]
            cv2.rectangle(annotated, (20, 30), (20 + text_size[0], 30 + text_size[1] + 10), color, -1)
            cv2.putText(annotated, label_text, (20, 50), font, font_scale, (255, 255, 255), thickness)
        return annotated

    def _add_result_info(self, layout: QHBoxLayout):
        if self.inspection_type == 'segmentation':
            total_defects = self.result.get('total_defects', 0)
            has_defects = self.result.get('has_defects', False)
            if has_defects:
                info_text = f' {total_defects} DEFEITO(S) ENCONTRADO(S)'
                info_color = 'orange'
            else:
                info_text = ' NENHUM DEFEITO ENCONTRADO'
                info_color = 'green'
        elif self.inspection_type == 'classification':
            status = self.result.get('status', 'unknown')
            defects_detected = self.result.get('defects_detected', False)
            if status == 'indeterminado':
                info_text = ' INDETERMINADO'
                info_color = 'orange'
            elif defects_detected:
                info_text = ' FRUTA RUIM'
                info_color = 'red'
            else:
                info_text = ' FRUTA BOA'
                info_color = 'green'
        label = QLabel(info_text)
        label.setStyleSheet(f'color: {info_color}; font-weight: bold; font-size: 14px;')
        layout.addWidget(label)
        layout.addStretch()

    def _numpy_to_pixmap(self, image: np.ndarray) -> QPixmap:
        if len(image.shape) == 3 and image.shape[2] == 3:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = image
        h, w = image_rgb.shape[:2]
        if len(image_rgb.shape) == 3:
            bytes_per_line = 3 * w
            qimage = QImage(image_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        else:
            bytes_per_line = w
            qimage = QImage(image_rgb.data, w, h, bytes_per_line, QImage.Format_Indexed8)
        return QPixmap.fromImage(qimage)

class CreateProfileDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Criar Novo Perfil')
        self.setGeometry(200, 200, 400, 150)
        self.setModal(True)
        layout = QVBoxLayout()
        label = QLabel('Nome do perfil:')
        layout.addWidget(label)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText('Ex: Brilho Alta, Noturno, Externo...')
        layout.addWidget(self.name_input)
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton(' Criar')
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)
        cancel_btn = QPushButton(' Cancelar')
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        self.name_input.setFocus()

    def get_profile_name(self) -> str:
        return self.name_input.text().strip()

class StreamingPopupWindow(QDialog):
    popup_closed = pyqtSignal()

    def __init__(self, core: SystemCore, parent=None):
        super().__init__(parent)
        self.core = core
        self.streaming_thread = None
        self.setWindowTitle(' Streaming de Câmera')
        self.setGeometry(100, 100, 800, 600)
        self.setModal(False)
        layout = QVBoxLayout()
        self.image_label = QLabel('Iniciando streaming...')
        self.image_label.setMinimumSize(640, 480)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet('border: 2px solid #555; background-color: #1a1a1a;')
        layout.addWidget(self.image_label)
        self.info_label = QLabel('FPS: -- | Resolução: --')
        layout.addWidget(self.info_label)
        close_btn = QPushButton(' Fechar Streaming')
        close_btn.clicked.connect(self.stop_streaming)
        layout.addWidget(close_btn)
        self.setLayout(layout)
        self.start_streaming()

    def start_streaming(self):
        self.streaming_thread = StreamingThread(self.core, target_fps=30)
        self.streaming_thread.frame_ready.connect(self._on_streaming_frame)
        self.streaming_thread.fps_info.connect(self._on_streaming_fps)
        self.streaming_thread.error_occurred.connect(self._on_streaming_error)
        self.streaming_thread.start()

    @pyqtSlot(np.ndarray)
    def _on_streaming_frame(self, frame: np.ndarray):
        try:
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                frame_rgb = frame
            h, w = frame_rgb.shape[:2]
            bytes_per_line = 3 * w if len(frame_rgb.shape) == 3 else w
            qimage = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888 if len(frame_rgb.shape) == 3 else QImage.Format_Indexed8)
            pixmap = QPixmap.fromImage(qimage)
            label_size = self.image_label.size()
            scaled_pixmap = pixmap.scaled(label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
        except Exception as e:
            log.debug(f'Erro ao exibir frame: {e}')

    @pyqtSlot(float)
    def _on_streaming_fps(self, fps: float):
        shape = '?' if not hasattr(self, '_current_frame') else self._current_frame.shape
        self.info_label.setText(f'FPS: {fps:.1f} | Resolução: --')

    @pyqtSlot(str)
    def _on_streaming_error(self, error_msg: str):
        QMessageBox.warning(self, 'Erro no Streaming', f'Erro: {error_msg}')
        self.close()

    def stop_streaming(self):
        if self.streaming_thread:
            self.streaming_thread.stop()
            self.streaming_thread = None
        self.close()

    def showEvent(self, event):
        log.info('  MainWindow showEvent triggered')
        super().showEvent(event)

    def closeEvent(self, event):
        log.info('  MainWindow closeEvent triggered')
        self.stop_streaming()
        self.popup_closed.emit()
        event.accept()

class MainWindow(QMainWindow):
    periodic_capture_ready = pyqtSignal(dict)

    def __init__(self, core: SystemCore):
        super().__init__()
        self.core = core
        self.capture_mgr = CaptureManagerQt(core, camera_profiles=None)
        self.inspection_mgr = InspectionManager(core)
        self.history_mgr = HistoryManager(core)
        self.pfs_mgr = BaslerProfileManager()
        self.capture_mgr.manager.camera_profiles = self.pfs_mgr
        try:
            if hasattr(self.capture_mgr, 'image_captured'):
                self.capture_mgr.image_captured.connect(self.on_image_captured)
            if hasattr(self.capture_mgr, 'error_occurred'):
                self.capture_mgr.error_occurred.connect(self.on_capture_error)
            if hasattr(self.inspection_mgr, 'inspection_completed'):
                self.inspection_mgr.inspection_completed.connect(self.on_inspection_completed)
            if hasattr(self.inspection_mgr, 'error_occurred'):
                self.inspection_mgr.error_occurred.connect(self.on_inspection_error)
        except Exception as e:
            log.warning(f'Erro ao conectar signals dos managers: {e}')
        self.current_image = None
        self.raw_image = None
        self.inspection_image = None
        self.inspection_raw_image = None
        self.current_results = None
        self.crop_enabled = False
        self.crop_bbox = None
        self._inspect_after_capture = None
        self.streaming_thread = None
        self.inspection_thread = None
        self.inspection_capture_thread = None
        self.streaming_popup = None
        self.camera_status_label = None
        self.camera_combo = None
        self.results_text = None
        self.logs_text = None
        self.setWindowTitle(DESKTOP_CONFIG['window_title'])
        self.setGeometry(100, 100, *DESKTOP_CONFIG['window_size'])
        self.setMinimumSize(800, 600)
        self._apply_theme()
        try:
            self._create_ui()
        except Exception as e:
            log.error(' Erro ao criar interface gráfica', exc_info=True)
            raise
        try:
            self._connect_core_callbacks()
        except Exception as e:
            log.warning(f'Erro ao conectar callbacks do core: {e}')
        if DESKTOP_CONFIG['show_system_tray']:
            try:
                self._create_system_tray()
            except Exception as e:
                log.warning(f'Erro ao criar system tray: {e}')
        log.info('  Interface desktop inicializada')
        QTimer.singleShot(100, self._update_camera_combo)
        QTimer.singleShot(5000, self._safe_update_camera_info)

    def _apply_theme(self):
        theme = DESKTOP_CONFIG['theme']
        if theme == 'dark':
            self.setStyleSheet('\n\n                QMainWindow {\n\n                    background-color: #2b2b2b;\n\n                    color: #ffffff;\n\n                }\n\n                QPushButton {\n\n                    background-color: #3c3c3c;\n\n                    color: white;\n\n                    border: 1px solid #555;\n\n                    padding: 8px;\n\n                    border-radius: 4px;\n\n                }\n\n                QPushButton:hover {\n\n                    background-color: #4a4a4a;\n\n                }\n\n                QPushButton:pressed {\n\n                    background-color: #2a2a2a;\n\n                }\n\n                QLabel {\n\n                    color: #ffffff;\n\n                }\n\n                QTextEdit, QTableWidget {\n\n                    background-color: #1e1e1e;\n\n                    color: #ffffff;\n\n                    border: 1px solid #555;\n\n                }\n\n                QTabWidget::pane {\n\n                    border: 1px solid #555;\n\n                    background-color: #2b2b2b;\n\n                }\n\n                QTabBar::tab {\n\n                    background-color: #3c3c3c;\n\n                    color: white;\n\n                    padding: 8px;\n\n                    margin-right: 2px;\n\n                }\n\n                QTabBar::tab:selected {\n\n                    background-color: #4a4a4a;\n\n                }\n\n                QGroupBox {\n\n                    border: 2px solid #555;\n\n                    border-radius: 5px;\n\n                    margin-top: 10px;\n\n                    padding-top: 10px;\n\n                    color: #ffffff;\n\n                }\n\n                QGroupBox::title {\n\n                    subcontrol-origin: margin;\n\n                    left: 10px;\n\n                    padding: 0 5px 0 5px;\n\n                }\n\n            ')
        elif theme == 'light':
            pass

    def _create_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        top_bar = QHBoxLayout()
        title_label = QLabel('SISTEMA DE INSPEÇÃO HÍBRIDO')
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        top_bar.addWidget(title_label)
        top_bar.addStretch()
        self.status_label = QLabel(' Conectado')
        top_bar.addWidget(self.status_label)
        main_layout.addLayout(top_bar)
        self.tab_widget = QTabWidget()
        self.tab_widget.setMinimumHeight(400)
        main_layout.addWidget(self.tab_widget, 1)
        self._create_capture_tab()
        self._create_inspection_tab()
        self._create_results_tab()
        self._create_pfs_tab()
        self._create_settings_tab()
        bottom_bar = QHBoxLayout()
        self.web_server_btn = QPushButton(' Iniciar Servidor Web')
        self.web_server_btn.clicked.connect(self.toggle_web_server)
        bottom_bar.addWidget(self.web_server_btn)
        bottom_bar.addStretch()
        self.log_btn = QPushButton(' Mostrar Log')
        self.log_btn.clicked.connect(self.show_log_window)
        bottom_bar.addWidget(self.log_btn)
        exit_btn = QPushButton(' Sair')
        exit_btn.clicked.connect(self.close)
        bottom_bar.addWidget(exit_btn)
        main_layout.addLayout(bottom_bar)

    def _create_capture_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        capture_group = QGroupBox('Controle de Câmera')
        capture_layout = QVBoxLayout()
        self.camera_info_label = QLabel('Câmera: Não inicializada')
        capture_layout.addWidget(self.camera_info_label)
        btn_layout = QHBoxLayout()
        self.capture_btn = QPushButton(' Capturar Imagem')
        self.capture_btn.clicked.connect(self.capture_image)
        self.capture_btn.setToolTip("Captura uma única imagem da câmera.\n\nO que faz:\n• Conecta à câmera (com fallback automático)\n• Captura 1 frame em alta qualidade\n• Aplica crop automático (se habilitado)\n• Exibe imagem neste painel\n\nUso:\n1. Posicione o produto\n2. Clique para capturar\n3. Vá para aba 'Inspeção' para analisar\n\n Para preview contínuo:\nclique em 'Captura Contínua'")
        btn_layout.addWidget(self.capture_btn)
        self.capture_continuous_btn = QPushButton(' Abrir Streaming')
        self.capture_continuous_btn.clicked.connect(lambda: self.toggle_continuous_capture(True))
        self.capture_continuous_btn.setToolTip('Ativa streaming em tempo real (30 FPS).\n\nO que faz:\n• Thread separada captura a cada 30ms\n• Mostra preview contínuo da câmera\n• Exibe FPS em tempo real\n• Sem travamento da interface\n\nUso:\n• Clique para iniciar streaming\n• Clique novamente para parar\n• Veja o FPS no canto inferior\n\n Perfeito para posicionar o produto')
        btn_layout.addWidget(self.capture_continuous_btn)
        capture_layout.addLayout(btn_layout)
        self.capture_timer = QTimer()
        self.capture_timer.timeout.connect(self.capture_image)
        capture_group.setLayout(capture_layout)
        layout.addWidget(capture_group)
        image_group = QGroupBox('Visualização')
        image_layout = QVBoxLayout()
        self.image_label = QLabel('Imagem aparecerá aqui')
        self.image_label.setMinimumSize(640, 480)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet('border: 2px solid #555; background-color: #1a1a1a;')
        image_layout.addWidget(self.image_label)
        self.image_info_label = QLabel('Sem imagem')
        image_layout.addWidget(self.image_info_label)
        image_group.setLayout(image_layout)
        layout.addWidget(image_group)
        periodic_group = QGroupBox(' Captura Periódica (dataset)')
        periodic_layout = QHBoxLayout()
        periodic_left = QVBoxLayout()
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel('Intervalo (s):'))
        self.periodic_interval = QSpinBox()
        self.periodic_interval.setRange(1, 3600)
        self.periodic_interval.setValue(10)
        interval_layout.addWidget(self.periodic_interval)
        periodic_left.addLayout(interval_layout)
        save_layout = QHBoxLayout()
        save_layout.addWidget(QLabel('Pasta de salvamento:'))
        self.periodic_save_dir = QLineEdit(str(Path.cwd() / 'data' / 'periodic'))
        save_layout.addWidget(self.periodic_save_dir)
        browse_btn = QPushButton('...')
        browse_btn.clicked.connect(self._browse_save_dir)
        save_layout.addWidget(browse_btn)
        periodic_left.addLayout(save_layout)
        periodic_layout.addLayout(periodic_left)
        periodic_right = QVBoxLayout()
        self.periodic_btn = QPushButton(' Iniciar Captura Periódica')
        self.periodic_btn.setCheckable(True)
        self.periodic_btn.clicked.connect(self._toggle_periodic_capture)
        periodic_right.addWidget(self.periodic_btn)
        periodic_right.addStretch()
        periodic_layout.addLayout(periodic_right)
        periodic_group.setLayout(periodic_layout)
        layout.addWidget(periodic_group)
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, ' Captura')
        self.update_camera_info()

    def _create_inspection_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        inspection_group = QGroupBox('Tipo de Inspeção')
        inspection_layout = QHBoxLayout()
        inspection_layout.setContentsMargins(5, 5, 5, 5)
        inspection_layout.setSpacing(5)
        inspection_layout.addWidget(QLabel('Tipo:'))
        self.inspection_type_combo = QComboBox()
        self.inspection_type_combo.addItems(['Segmentação', 'Classificação'])
        self.inspection_type_combo.currentIndexChanged.connect(self._on_inspection_type_changed)
        inspection_layout.addWidget(self.inspection_type_combo)
        inspection_layout.addWidget(QLabel('Modelo:'))
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(150)
        self.model_combo.setMaximumWidth(250)
        inspection_layout.addWidget(self.model_combo)
        self._on_inspection_type_changed()
        inspection_layout.addWidget(QLabel('Threshold:'))
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.0, 1.0)
        self.confidence_spin.setSingleStep(0.05)
        self.confidence_spin.setValue(0.7)
        self.confidence_spin.setMaximumWidth(80)
        inspection_layout.addWidget(self.confidence_spin)
        model_reload_btn = QPushButton(' Recarregar')
        model_reload_btn.clicked.connect(self.reload_models)
        model_reload_btn.setMaximumWidth(110)
        inspection_layout.addWidget(model_reload_btn)
        self.inspect_btn = QPushButton(' Executar')
        self.inspect_btn.clicked.connect(self.perform_inspection)
        self.inspect_btn.setEnabled(True)
        self.inspect_btn.setMaximumWidth(120)
        self.inspect_btn.setToolTip('Executa análise inteligente na imagem.\nSegmentação: Detecta defeitos (bbox)\nClassificação: Classifica BOM ou RUIM')
        inspection_layout.addWidget(self.inspect_btn)
        inspection_layout.addStretch()
        inspection_group.setLayout(inspection_layout)
        inspection_group.setMaximumHeight(70)
        layout.addWidget(inspection_group, 0)
        self.inspection_results_panel = InspectionResultsPanel()
        layout.addWidget(self.inspection_results_panel, 1)
        actions_group = QGroupBox('Ações')
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(8, 8, 8, 8)
        actions_layout.setSpacing(8)
        self.vp_btn = QPushButton('Verdadeiro Positivo')
        self.vp_btn.clicked.connect(lambda: self._save_categoria('verdadeiro_positivo'))
        self.vp_btn.setEnabled(False)
        self.vp_btn.setMaximumWidth(140)
        self.vp_btn.setMinimumHeight(32)
        self.vp_btn.setToolTip('Move a imagem para data/verdadeiro_positivo')
        actions_layout.addWidget(self.vp_btn)
        self.vn_btn = QPushButton('Verdadeiro Negativo')
        self.vn_btn.clicked.connect(lambda: self._save_categoria('verdadeiro_negativo'))
        self.vn_btn.setEnabled(False)
        self.vn_btn.setMaximumWidth(140)
        self.vn_btn.setMinimumHeight(32)
        self.vn_btn.setToolTip('Move a imagem para data/verdadeiro_negativo')
        actions_layout.addWidget(self.vn_btn)
        self.fp_btn = QPushButton('Falso Positivo')
        self.fp_btn.clicked.connect(lambda: self._save_categoria('falso_positivo'))
        self.fp_btn.setEnabled(False)
        self.fp_btn.setMaximumWidth(140)
        self.fp_btn.setMinimumHeight(32)
        self.fp_btn.setToolTip('Move a imagem para data/falso_positivo')
        actions_layout.addWidget(self.fp_btn)
        self.fn_btn = QPushButton('Falso Negativo')
        self.fn_btn.clicked.connect(lambda: self._save_categoria('falso_negativo'))
        self.fn_btn.setEnabled(False)
        self.fn_btn.setMaximumWidth(140)
        self.fn_btn.setMinimumHeight(32)
        self.fn_btn.setToolTip('Move a imagem para data/falso_negativo')
        actions_layout.addWidget(self.fn_btn)
        self.copy_results_btn = QPushButton(' Copiar Resultados')
        self.copy_results_btn.clicked.connect(self._copy_inspection_results)
        self.copy_results_btn.setEnabled(False)
        self.copy_results_btn.setMaximumWidth(160)
        self.copy_results_btn.setMinimumHeight(32)
        self.copy_results_btn.setToolTip('Copia os resultados para a área de transferência')
        actions_layout.addWidget(self.copy_results_btn)
        self.export_image_btn = QPushButton(' Exportar Imagem')
        self.export_image_btn.clicked.connect(self._export_inspection_image)
        self.export_image_btn.setEnabled(False)
        self.export_image_btn.setMaximumWidth(160)
        self.export_image_btn.setMinimumHeight(32)
        self.export_image_btn.setToolTip('Salva a imagem anotada em arquivo')
        actions_layout.addWidget(self.export_image_btn)
        self.clear_btn = QPushButton(' Limpar')
        self.clear_btn.clicked.connect(self._clear_inspection_results)
        self.clear_btn.setMaximumWidth(100)
        self.clear_btn.setMinimumHeight(32)
        self.clear_btn.setToolTip('Remove os resultados exibidos')
        actions_layout.addWidget(self.clear_btn)
        actions_layout.addStretch()
        actions_group.setLayout(actions_layout)
        actions_group.setMaximumHeight(90)
        layout.addWidget(actions_group, 0)
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, ' Inspeção')

    def _create_results_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        filters_group = QGroupBox('Filtros')
        filters_layout = QHBoxLayout()
        filters_layout.addWidget(QLabel('Tipo:'))
        self.history_type_combo = QComboBox()
        self.history_type_combo.addItem('Carregando...')
        filters_layout.addWidget(self.history_type_combo)
        filters_layout.addWidget(QLabel('Modelo:'))
        self.history_model_combo = QComboBox()
        self.history_model_combo.setEditable(True)
        self.history_model_combo.addItem('Carregando...')
        filters_layout.addWidget(self.history_model_combo)
        filters_layout.addStretch()
        filters_group.setLayout(filters_layout)
        layout.addWidget(filters_group)
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels(['Data/Hora', 'Tipo', 'Modelo', 'Resultado', 'Defeitos', 'Máscara'])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setMinimumHeight(300)
        self.history_result_dirs = []
        self.history_table.cellDoubleClicked.connect(self._history_row_double_clicked)
        layout.addWidget(self.history_table, 1)
        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton(' Atualizar')
        refresh_btn.clicked.connect(self.load_history)
        btn_layout.addWidget(refresh_btn)
        export_btn = QPushButton(' Exportar CSV')
        export_btn.clicked.connect(self.export_history)
        btn_layout.addWidget(export_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, ' Histórico')

    def _create_pfs_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        title = QLabel(' Gerenciamento de Perfis Basler (.pfs)')
        title.setFont(QFont('Arial', 14, QFont.Bold))
        layout.addWidget(title)
        controls_group = QGroupBox('Controles')
        controls_layout = QHBoxLayout()
        self.load_pfs_btn = QPushButton(' Carregar .pfs')
        self.load_pfs_btn.clicked.connect(self.load_pfs_file)
        controls_layout.addWidget(self.load_pfs_btn)
        self.save_pfs_btn = QPushButton(' Salvar .pfs')
        self.save_pfs_btn.clicked.connect(self.save_pfs_file)
        controls_layout.addWidget(self.save_pfs_btn)
        self.refresh_pfs_btn = QPushButton(' Atualizar')
        self.refresh_pfs_btn.clicked.connect(self.refresh_pfs_list)
        controls_layout.addWidget(self.refresh_pfs_btn)
        controls_layout.addStretch()
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)
        profiles_group = QGroupBox('Perfis .pfs Disponíveis')
        profiles_layout = QVBoxLayout()
        profile_layout = QHBoxLayout()
        profile_layout.addWidget(QLabel('Perfil:'))
        self.pfs_profile_combo = QComboBox()
        self.pfs_profile_combo.currentTextChanged.connect(self.on_pfs_profile_selected)
        profile_layout.addWidget(self.pfs_profile_combo)
        self.delete_pfs_btn = QPushButton(' Excluir')
        self.delete_pfs_btn.clicked.connect(self.delete_pfs_profile)
        profile_layout.addWidget(self.delete_pfs_btn)
        profiles_layout.addLayout(profile_layout)
        self.pfs_params_table = QTableWidget()
        self.pfs_params_table.setColumnCount(3)
        self.pfs_params_table.setHorizontalHeaderLabels(['Parâmetro', 'Valor', 'Ações'])
        self.pfs_params_table.horizontalHeader().setStretchLastSection(True)
        self.pfs_params_table.setAlternatingRowColors(False)
        self.pfs_params_table.setStyleSheet('\n\n            QTableWidget {\n\n                background-color: #1a1a1a;\n\n                color: white;\n\n                gridline-color: #333;\n\n            }\n\n            QTableWidget::item {\n\n                background-color: #1a1a1a;\n\n                color: white;\n\n                border: 1px solid #333;\n\n            }\n\n            QTableWidget::item:selected {\n\n                background-color: #2a2a2a;\n\n                color: white;\n\n            }\n\n            QHeaderView::section {\n\n                background-color: #2a2a2a;\n\n                color: white;\n\n                border: 1px solid #333;\n\n                padding: 4px;\n\n            }\n\n        ')
        self.pfs_params_table.setMinimumHeight(250)
        profiles_layout.addWidget(self.pfs_params_table, 1)
        profiles_group.setLayout(profiles_layout)
        layout.addWidget(profiles_group)
        info_group = QGroupBox('Informações do Perfil')
        info_layout = QVBoxLayout()
        self.pfs_info_text = QTextEdit()
        self.pfs_info_text.setMaximumHeight(100)
        self.pfs_info_text.setReadOnly(True)
        info_layout.addWidget(self.pfs_info_text)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, ' Perfis Camêra Bassler')

    def _create_settings_tab(self):
        tab = QWidget()
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet('\n\n            QWidget {\n\n                background-color: #2b2b2b;\n\n                color: #ffffff;\n\n            }\n\n            QGroupBox {\n\n                border: 2px solid #555;\n\n                border-radius: 5px;\n\n                margin-top: 10px;\n\n                padding-top: 10px;\n\n                color: #ffffff;\n\n                font-weight: bold;\n\n            }\n\n            QGroupBox::title {\n\n                subcontrol-origin: margin;\n\n                left: 10px;\n\n                padding: 0 5px 0 5px;\n\n                color: #ffffff;\n\n            }\n\n            QLabel {\n\n                color: #ffffff;\n\n            }\n\n            QPushButton {\n\n                background-color: #3c3c3c;\n\n                color: white;\n\n                border: 1px solid #555;\n\n                padding: 8px;\n\n                border-radius: 4px;\n\n            }\n\n            QPushButton:hover {\n\n                background-color: #4a4a4a;\n\n            }\n\n            QPushButton:pressed {\n\n                background-color: #2a2a2a;\n\n            }\n\n            QComboBox {\n\n                background-color: #3c3c3c;\n\n                color: white;\n\n                border: 1px solid #555;\n\n                padding: 4px;\n\n                border-radius: 2px;\n\n                min-height: 24px;\n\n                min-width: 100px;\n\n            }\n\n            QComboBox:hover {\n\n                border: 1px solid #777;\n\n                background-color: #4a4a4a;\n\n            }\n\n            QComboBox:focus {\n\n                border: 2px solid #0d47a1;\n\n                background-color: #454545;\n\n            }\n\n            QComboBox::drop-down {\n\n                border: none;\n\n                width: 30px;\n\n                background-color: transparent;\n\n            }\n\n            /* use default Qt down-arrow icon */\n\n            QComboBox::down-arrow {\n\n                /* no custom styling */\n\n            }\n\n            QComboBox:on {\n\n                background-color: #454545;\n\n                border: 2px solid #0d47a1;\n\n            }\n\n            QComboBox QAbstractItemView {\n\n                background-color: #3c3c3c;\n\n                color: white;\n\n                border: 1px solid #555;\n\n                selection-background-color: #0d47a1;\n\n                selection-color: white;\n\n            }\n\n            QComboBox QAbstractItemView::item:hover {\n\n                background-color: #505050;\n\n            }\n\n            QComboBox QAbstractItemView::item:selected {\n\n                background-color: #0d47a1;\n\n            }\n\n            QSpinBox, QDoubleSpinBox {\n\n                background-color: #3c3c3c;\n\n                color: white;\n\n                border: 1px solid #555;\n\n                padding: 4px;\n\n                border-radius: 2px;\n\n            }\n\n            QCheckBox {\n\n                color: #ffffff;\n\n            }\n\n            QCheckBox::indicator {\n\n                width: 16px;\n\n                height: 16px;\n\n                background-color: #3c3c3c;\n\n                border: 1px solid #555;\n\n                border-radius: 2px;\n\n            }\n\n            QCheckBox::indicator:checked {\n\n                background-color: #4a4a4a;\n\n            }\n\n            QLineEdit {\n\n                background-color: #3c3c3c;\n\n                color: white;\n\n                border: 1px solid #555;\n\n                padding: 4px;\n\n                border-radius: 2px;\n\n            }\n\n        ')
        layout = QVBoxLayout(scroll_widget)
        camera_group = QGroupBox('Configurações da Câmera')
        camera_layout = QVBoxLayout()
        self.camera_status_label = QLabel(' Câmera: Não inicializada')
        self.camera_status_label.setStyleSheet('font-weight: bold; font-size: 12px;')
        camera_layout.addWidget(self.camera_status_label)
        cam_select_layout = QHBoxLayout()
        cam_select_layout.addWidget(QLabel('Trocar câmera:'))
        self.camera_combo = QComboBox()
        self.camera_combo.setMinimumWidth(150)
        self.camera_combo.setMinimumHeight(28)
        self.camera_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.camera_combo.setMaxVisibleItems(10)
        self.camera_combo.setEditable(False)
        self.camera_combo.setFocusPolicy(3)
        self.camera_combo.currentIndexChanged.connect(self._on_camera_combo_changed)
        cam_select_layout.addWidget(self.camera_combo)
        camera_layout.addLayout(cam_select_layout)
        reload_btn = QPushButton(' Recarregar')
        reload_btn.setToolTip('Reconecta todas as câmeras e atualiza lista')
        reload_btn.clicked.connect(self._reload_cameras_completely)
        camera_layout.addWidget(reload_btn)
        camera_group.setLayout(camera_layout)
        layout.addWidget(camera_group)
        system_group = QGroupBox('Configurações do Sistema')
        system_layout = QVBoxLayout()
        self.auto_save_check = QCheckBox('Salvar resultados automaticamente')
        self.auto_save_check.setChecked(True)
        system_layout.addWidget(self.auto_save_check)
        self.auto_web_check = QCheckBox('Iniciar servidor web automaticamente')
        self.auto_web_check.setChecked(False)
        system_layout.addWidget(self.auto_web_check)
        self.stream_popup_check = QCheckBox('Abrir streaming em janela popup')
        self.stream_popup_check.setChecked(DESKTOP_CONFIG.get('stream_in_popup', True))
        self.stream_popup_check.stateChanged.connect(self._on_stream_in_popup_toggled)
        system_layout.addWidget(self.stream_popup_check)
        system_group.setLayout(system_layout)
        layout.addWidget(system_group)
        crop_group = QGroupBox('Crop / Pré-processamento')
        crop_layout = QVBoxLayout()
        crop_controls = QHBoxLayout()
        self.crop_check = QCheckBox('Habilitar Crop automático')
        self.crop_check.setChecked(False)
        self.crop_check.stateChanged.connect(self._on_crop_toggled)
        crop_controls.addWidget(self.crop_check)
        self.edit_crop_btn = QPushButton('Editar Crop')
        self.edit_crop_btn.clicked.connect(self._open_crop_editor)
        crop_controls.addWidget(self.edit_crop_btn)
        self.reset_crop_btn = QPushButton('Resetar Crop')
        self.reset_crop_btn.clicked.connect(self._reset_crop)
        crop_controls.addWidget(self.reset_crop_btn)
        self.reset_and_capture_btn = QPushButton('Reset + Capturar')
        self.reset_and_capture_btn.clicked.connect(self._reset_crop_and_capture)
        crop_controls.addWidget(self.reset_and_capture_btn)
        crop_layout.addLayout(crop_controls)
        self.crop_info_label = QLabel('Crop: nenhum')
        crop_layout.addWidget(self.crop_info_label)
        crop_group.setLayout(crop_layout)
        layout.addWidget(crop_group)
        logs_group = QGroupBox(' Logs do Sistema')
        logs_layout = QVBoxLayout()
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setMaximumHeight(150)
        self.logs_text.setPlaceholderText('Logs do sistema aparecem aqui...')
        logs_layout.addWidget(self.logs_text)
        log_btn_layout = QHBoxLayout()
        clear_logs_btn = QPushButton(' Limpar Logs')
        clear_logs_btn.clicked.connect(self._clear_logs)
        log_btn_layout.addWidget(clear_logs_btn)
        export_logs_btn = QPushButton(' Exportar Logs')
        export_logs_btn.clicked.connect(self._export_logs)
        log_btn_layout.addWidget(export_logs_btn)
        log_btn_layout.addStretch()
        logs_layout.addLayout(log_btn_layout)
        logs_group.setLayout(logs_layout)
        layout.addWidget(logs_group)
        layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        tab_layout = QVBoxLayout(tab)
        tab_layout.addWidget(scroll_area)
        tab.setLayout(tab_layout)
        self.tab_widget.addTab(tab, ' Configurações')

    def _create_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        app_icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
        self.tray_icon.setIcon(app_icon)
        tray_menu = QMenu()
        show_action = QAction('Mostrar', self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        hide_action = QAction('Ocultar', self)
        hide_action.triggered.connect(self.hide)
        tray_menu.addAction(hide_action)
        tray_menu.addSeparator()
        quit_action = QAction('Sair', self)
        quit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

    def _safe_update_camera_info(self):
        try:
            log.debug('Inicializando filtros de histórico...')
            if self.history_type_combo:
                self.history_type_combo.blockSignals(True)
                self.history_type_combo.clear()
                self.history_type_combo.addItems(['Todos', 'Segmentação', 'Classificação'])
                self.history_type_combo.blockSignals(False)
                try:
                    if not self.history_type_combo.currentTextChanged.isSignalConnected():
                        self.history_type_combo.currentTextChanged.connect(self.load_history)
                except Exception as e:
                    log.debug(f'Signal já estava conectado: {e}')
            if self.history_model_combo:
                self.history_model_combo.blockSignals(True)
                self.history_model_combo.clear()
                self.history_model_combo.addItem('Todos')
                self.history_model_combo.blockSignals(False)
                try:
                    if not self.history_model_combo.currentTextChanged.isSignalConnected():
                        self.history_model_combo.currentTextChanged.connect(self.load_history)
                except Exception as e:
                    log.debug(f'Signal já estava conectado: {e}')
            log.debug('Carregando histórico inicial...')
            try:
                self.load_history()
            except Exception as e:
                log.warning(f'Erro ao carregar histórico: {e}')
                self.log_message(f' Erro ao carregar histórico: {e}')
            log.debug('Carregando lista de perfis PFS...')
            try:
                self.refresh_pfs_list()
            except Exception as e:
                log.warning(f'Erro ao carregar perfis PFS: {e}')
                self.log_message(f' Erro ao carregar perfis PFS: {e}')
            log.debug('Atualizando informações da câmera...')
            try:
                self.update_camera_info()
            except Exception as e:
                log.warning(f'Erro ao atualizar câmera: {e}')
                self.log_message(f' Erro ao atualizar câmera: {e}')
        except Exception as e:
            log.error(f'Erro crítico em _safe_update_camera_info: {e}', exc_info=True)

    def _connect_core_callbacks(self):

        def on_capture_completed(data):
            try:
                QTimer.singleShot(100, lambda: self.log_message(f" Captura completada: {data.get('camera_info', {}).get('type', 'N/A')}"))
            except Exception as e:
                log.warning(f'Erro ao agendar callback capture_completed: {e}')

        def on_inspection_completed(data, inspection_type):
            try:
                self.log_message(f' {inspection_type.capitalize()} completada')
            except Exception as e:
                log.warning(f'Erro ao log inspection_completed: {e}')
        try:
            self.core.register_callback('capture_completed', on_capture_completed)
        except Exception as e:
            log.warning(f'Erro ao registrar callback capture_completed: {e}')

        def on_periodic_saved(data):
            try:
                self.periodic_capture_ready.emit(data)
            except Exception as e:
                log.warning(f'Erro em on_periodic_saved: {e}')
        try:
            self.core.register_callback('periodic_capture_saved', on_periodic_saved)
        except Exception as e:
            log.warning(f'Erro ao registrar callback periodic_capture_saved: {e}')
        self.periodic_capture_ready.connect(self._on_periodic_capture_ready)

    def update_camera_info(self):
        try:
            if not self.camera_status_label:
                log.debug('camera_status_label não foi criado ainda')
                return
            try:
                info = self.core.get_system_info()
            except Exception as e:
                log.warning(f'get_system_info falhou: {e}')
                self.camera_status_label.setText(' Câmera não respondendo')
                return
            camera_info = info.get('camera', {})
            camera_type = camera_info.get('type', 'Desconhecida').upper()
            status = '' if camera_info.get('initialized', False) else ''
            width = camera_info.get('width', '?')
            height = camera_info.get('height', '?')
            model = camera_info.get('model', '')
            status_text = f' {camera_type} {status} '
            if model:
                status_text += f'({model}) '
            status_text += f'\n{width}x{height}'
            self.camera_status_label.setText(status_text)
            if self.camera_combo is not None:
                self._update_camera_combo()
            else:
                log.debug('camera_combo ainda não foi criado')
        except Exception as e:
            log.error(f'Erro ao atualizar info da câmera: {e}', exc_info=True)
            if self.camera_status_label:
                self.camera_status_label.setText(' Erro na câmera')

    def _reload_cameras_completely(self):
        self.log_message(' Reacarregando câmeras...')
        try:
            if self.core.camera_manager:
                self.core.camera_manager.release()
            from core.camera.camera_manager import CameraManager
            from config import CAMERA_CONFIG
            self.core.camera_manager = CameraManager(CAMERA_CONFIG)
            if self.core.camera_manager.initialize():
                self.log_message(' Câmeras recarregadas com sucesso')
                log.info('Câmeras recarregadas')
            else:
                self.log_message(' Nenhuma câmera disponível')
                log.warning('Nenhuma câmera conseguiu inicializar')
            self._update_camera_combo()
            self.update_camera_info()
        except Exception as e:
            msg = f'Erro ao recarregar câmeras: {e}'
            self.log_message(f' {msg}')
            log.error(msg)

    def _update_camera_combo(self):
        try:
            if self.camera_combo is None:
                log.debug('camera_combo não foi criado ainda')
                return
            if self.camera_combo.signalsBlocked():
                log.debug('_update_camera_combo: combo já está sendo atualizado, ignorando')
                return
            cameras = self.core.get_available_cameras()
            log.debug(f'_update_camera_combo: {len(cameras)} câmeras detectadas')
            self.camera_combo.blockSignals(True)
            try:
                self.camera_combo.clear()
                current_active_index = None
                for cam_info in cameras:
                    cam_type = cam_info.get('type', 'unknown').upper()
                    position = cam_info.get('position', 0)
                    is_active = cam_info.get('is_active', False)
                    available = cam_info.get('available', False)
                    connected = cam_info.get('connected', False)
                    model = cam_info.get('model', '')
                    resolution = cam_info.get('resolution', '')
                    if is_active:
                        icon = ''
                    elif connected:
                        icon = ''
                    elif available:
                        icon = ''
                    else:
                        icon = ''
                    label = f'{cam_type} #{position} {icon}'
                    if model and model != 'N/A':
                        label += f' - {model}'
                    self.camera_combo.addItem(label, userData=position)
                    if is_active:
                        current_active_index = self.camera_combo.count() - 1
                    log.debug(f'  Câmera adicionada: {label} (position={position}, ativa={is_active})')
                if self.camera_combo.count() == 0:
                    self.camera_combo.addItem(' Aguardando câmeras...', userData=-1)
                    log.warning('Nenhuma câmera detectada, adicionando placeholder')
                if current_active_index is not None:
                    self.camera_combo.setCurrentIndex(current_active_index)
                    log.debug(f'Câmera ativa selecionada no índice {current_active_index}')
                elif self.camera_combo.count() > 0:
                    self.camera_combo.setCurrentIndex(0)
                    log.debug(f'Primeira câmera selecionada no índice 0')
                self.camera_combo.setEnabled(True)
                max_width = 150
                for i in range(self.camera_combo.count()):
                    text_width = len(self.camera_combo.itemText(i)) * 8
                    if text_width > max_width:
                        max_width = min(text_width, 400)
                self.camera_combo.setMinimumWidth(max_width)
                log.debug(f'Combo atualizado com sucesso: {self.camera_combo.count()} itens, combo habilitado, largura={max_width}px')
            finally:
                self.camera_combo.blockSignals(False)
        except Exception as e:
            log.error(f'Erro ao atualizar combo de câmeras: {e}', exc_info=True)
            self.log_message(f' Erro ao atualizar lista de câmeras: {e}')
            if self.camera_combo:
                self.camera_combo.setEnabled(True)

    def _on_camera_combo_changed(self, index: int):
        if index < 0 or not self.camera_combo:
            return
        try:
            camera_index = self.camera_combo.itemData(index)
            if camera_index is None or not isinstance(camera_index, int):
                log.debug(f'_on_camera_combo_changed: item {index} sem dados válidos')
                return
            if camera_index < 0:
                log.debug(f'_on_camera_combo_changed: item é placeholder, ignorando')
                return
            cameras = self.core.get_available_cameras()
            current_active = next((c for c in cameras if c.get('is_active')), None)
            if current_active and current_active.get('position') == camera_index:
                log.debug(f'Câmera {camera_index} já está ativa, ignorando')
                return
            was_blocked = self.camera_combo.signalsBlocked()
            if not was_blocked:
                self.camera_combo.blockSignals(True)
            try:
                self.log_message(f' Conectando câmera {camera_index}...')
                log.info(f'Alternando para câmera {camera_index}')
                if self.core.switch_camera(camera_index):
                    self.log_message(f' Câmera {camera_index} conectada com sucesso')
                    log.info(f'Câmera {camera_index} conectada com sucesso')
                    QTimer.singleShot(300, self._safe_update_after_switch)
                else:
                    self.log_message(f' Não foi possível conectar câmera {camera_index}')
                    log.warning(f'Falha ao conectar câmera {camera_index}')
                    QTimer.singleShot(100, self._update_camera_combo)
            finally:
                if not was_blocked:
                    self.camera_combo.blockSignals(False)
        except Exception as e:
            self.log_message(f' Erro ao trocar câmera: {e}')
            log.error(f'Erro em _on_camera_combo_changed: {e}', exc_info=True)
            QTimer.singleShot(100, self._update_camera_combo)

    def _safe_update_after_switch(self):
        try:
            log.debug('Atualizando interface após mudança de câmera...')
            self.update_camera_info()
            log.debug('Info da câmera atualizada')
            self._update_camera_combo()
            log.debug('Combo de câmeras atualizado após switch')
        except Exception as e:
            log.error(f'Erro ao atualizar após switch de câmera: {e}', exc_info=True)
            self.log_message(f' Erro ao atualizar após mudança de câmera: {e}')

    def _on_crop_toggled(self, state: int):
        self.crop_enabled = bool(state)
        self.capture_mgr.set_crop_settings(self.crop_enabled, self.crop_bbox)
        self.crop_info_label.setText(f"Crop: {('ativo' if self.crop_enabled else 'inativo')}")
        self.log_message(f" Crop automático {('ativado' if self.crop_enabled else 'desativado')}")

    def _reset_crop(self):
        self.crop_bbox = None
        self.crop_enabled = False
        self.capture_mgr.reset_crop()
        self.crop_check.setChecked(False)
        self.crop_info_label.setText('Crop: nenhum')
        self.log_message(' Crop resetado')

    def _reset_crop_and_capture(self):
        self._reset_crop()
        QTimer.singleShot(50, self.capture_image)

    def _on_stream_in_popup_toggled(self, state: int):
        enabled = bool(state)
        DESKTOP_CONFIG['stream_in_popup'] = enabled
        self.log_message(f" Streaming em popup {('habilitado' if enabled else 'desabilitado')}")

    def _open_crop_editor(self):
        img_for_edit = self.capture_mgr.get_raw_image() if self.capture_mgr.get_raw_image() is not None else self.capture_mgr.get_current_image()
        if img_for_edit is None:
            QMessageBox.warning(self, 'Sem Imagem', 'Capture uma imagem para editar o crop')
            return
        dlg = CropDialog(img_for_edit, parent=self)
        if dlg.exec_() == QDialog.Accepted and dlg.bbox:
            self.crop_bbox = dlg.bbox
            self.capture_mgr.set_crop_settings(self.crop_enabled, self.crop_bbox)
            self.crop_info_label.setText(f'Crop: {self.crop_bbox}')
            self.log_message(f' Crop definido: {self.crop_bbox}')

    def _browse_save_dir(self):
        dirpath = QFileDialog.getExistingDirectory(self, 'Escolher pasta', str(Path.cwd()))
        if dirpath:
            self.periodic_save_dir.setText(dirpath)

    @pyqtSlot(dict)
    def _on_periodic_capture_ready(self, data: dict):
        try:
            path = data.get('path')
            ts = datetime.fromtimestamp(data.get('timestamp', time.time())).isoformat()
            if path and Path(path).exists():
                image = cv2.imread(path)
                if image is not None:
                    self.current_image = image
                    h, w = image.shape[:2]
                    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    bytes_per_line = 3 * w
                    qimage = QImage(image_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    pixmap = QPixmap.fromImage(qimage)
                    scaled_pixmap = pixmap.scaledToWidth(640, Qt.SmoothTransformation)
                    self.image_label.setPixmap(scaled_pixmap)
                    self.image_info_label.setText(f' Captura periódica: {w}x{h} | {path}')
                    self.log_message(f' Captura periódica salva e exibida: {path} @ {ts}')
                else:
                    self.log_message(f' Erro ao carregar imagem: {path}')
            else:
                self.log_message(f' Arquivo não encontrado: {path}')
        except Exception as e:
            log.error(f'Erro ao exibir captura periódica: {e}')
            self.log_message(f' Erro ao exibir captura periódica: {e}')

    def _toggle_periodic_capture(self, checked: bool):
        if checked:
            interval = float(self.periodic_interval.value())
            save_dir = self.periodic_save_dir.text()
            try:
                ops = None
                if self.crop_enabled and self.crop_bbox:
                    ops = [{'name': 'crop', 'bbox': self.crop_bbox}]
                self.core.start_periodic_capture(interval, save_dir, preprocess_ops=ops)
                self.periodic_btn.setText('⏸ Parar Captura Periódica')
                self.log_message(f' Captura periódica iniciada (intervalo {interval}s) -> {save_dir}')
            except Exception as e:
                QMessageBox.critical(self, 'Erro', f'Não foi possível iniciar captura periódica:\n{e}')
                self.periodic_btn.setChecked(False)
        else:
            try:
                self.core.stop_periodic_capture()
                self.periodic_btn.setText(' Iniciar Captura Periódica')
                self.log_message('⏸ Captura periódica parada')
            except Exception as e:
                QMessageBox.warning(self, 'Erro', f'Erro ao parar captura periódica:\n{e}')

    def capture_image(self):
        self.capture_btn.setEnabled(False)
        self.status_label.setText(' Capturando...')
        try:
            self.capture_mgr.capture_image()
        except Exception as e:
            log.error(f'Erro ao iniciar captura pelo manager: {e}')
            self.capture_thread = CaptureThread(self.core)
            self.capture_thread.image_captured.connect(self.on_image_captured)
            self.capture_thread.error_occurred.connect(self.on_capture_error)
            self.capture_thread.start()

    @pyqtSlot(dict)
    def on_image_captured(self, result: dict):
        self.capture_btn.setEnabled(True)
        self.status_label.setText(' Pronto')
        processed_result = result
        if processed_result is None:
            return
        self.raw_image = processed_result.get('raw_image')
        self.current_image = processed_result.get('image')
        self.display_image(self.current_image)
        shape = processed_result.get('shape', 'N/A')
        self.image_info_label.setText(f"Resolução: {shape} | Câmera: {processed_result.get('camera_info', {}).get('type', 'N/A')} | Hora: {processed_result.get('timestamp', 'N/A')}")
        self.log_message(f' Imagem capturada: {shape}')
        if self.capture_mgr.should_inspect_after_capture():
            try:
                inspection_type = self.capture_mgr.should_inspect_after_capture()
                ui_text = 'Segmentação' if inspection_type == 'segmentation' else 'Classificação'
                self.capture_mgr.set_inspect_after_capture(None)
                QTimer.singleShot(50, lambda: self._start_inspection(inspection_type, ui_text))
            except Exception as e:
                self.log_message(f' Falha ao iniciar inspeção após captura: {e}')

    @pyqtSlot(str)
    def on_capture_error(self, error_msg: str):
        self.capture_btn.setEnabled(True)
        self.status_label.setText(' Erro')
        QMessageBox.warning(self, 'Erro na Captura', f'Falha ao capturar imagem:\n{error_msg}')
        self.log_message(f' Erro na captura: {error_msg}')

    def display_image(self, image: np.ndarray):
        if image is None:
            return
        image_rgb = self.capture_mgr.get_image_for_display()
        if image_rgb is None:
            return
        h, w = image_rgb.shape[:2]
        if len(image_rgb.shape) == 3:
            ch = image_rgb.shape[2]
            bytes_per_line = ch * w
            qimage = QImage(image_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        else:
            bytes_per_line = w
            qimage = QImage(image_rgb.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
        pixmap = QPixmap.fromImage(qimage)
        label_size = self.image_label.size()
        scaled_pixmap = pixmap.scaled(label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)

    def _on_streaming_frame(self, frame: np.ndarray):
        try:
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                frame_rgb = frame
            h, w = frame_rgb.shape[:2]
            bytes_per_line = 3 * w if len(frame_rgb.shape) == 3 else w
            qimage = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888 if len(frame_rgb.shape) == 3 else QImage.Format_Indexed8)
            pixmap = QPixmap.fromImage(qimage)
            label_size = self.image_label.size()
            scaled_pixmap = pixmap.scaled(label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
        except Exception as e:
            log.debug(f'Erro ao exibir frame: {e}')

    def _on_streaming_fps(self, fps: float):
        self.info_label.setText(f'FPS: {fps:.1f} | Resolução: --')

    def _on_streaming_error(self, error_msg: str):
        QMessageBox.warning(self, 'Erro no Streaming', f'Erro: {error_msg}')
        if hasattr(self, 'streaming_thread') and self.streaming_thread:
            try:
                self.streaming_thread.stop()
            except Exception:
                pass
            self.streaming_thread = None
        self.capture_continuous_btn.setEnabled(True)
        self.log_message(' Streaming interrompido devido a erro')

    def toggle_continuous_capture(self, checked: bool):
        use_popup = DESKTOP_CONFIG.get('stream_in_popup', True)
        if not use_popup:
            if hasattr(self, 'streaming_thread') and self.streaming_thread:
                try:
                    self.streaming_thread.stop()
                except Exception:
                    pass
                self.streaming_thread = None
                self.capture_continuous_btn.setEnabled(True)
                self.log_message(' Streaming interrompido')
                return
            self.streaming_thread = StreamingThread(self.core, target_fps=30)
            self.streaming_thread.frame_ready.connect(self._on_streaming_frame)
            self.streaming_thread.fps_info.connect(self._on_streaming_fps)
            self.streaming_thread.error_occurred.connect(self._on_streaming_error)
            self.streaming_thread.start()
            self.capture_continuous_btn.setEnabled(False)
            self.log_message(' Streaming iniciado (inline)')
            return
        self.streaming_popup = StreamingPopupWindow(self.core, parent=self)
        self.streaming_popup.popup_closed.connect(self._on_streaming_popup_closed)
        self.streaming_popup.show()
        self.capture_continuous_btn.setEnabled(False)
        self.log_message(' Janela de streaming aberta')

    def _on_streaming_popup_closed(self):
        self.capture_continuous_btn.setEnabled(True)
        self.streaming_popup = None
        self.log_message('⏸ Streaming fechado')

    def _on_inspection_type_changed(self):
        try:
            ui_text = self.inspection_type_combo.currentText()
            model_type = 'classification' if 'Classificação' in ui_text else 'segmentation'
            available_models = get_available_models(model_type)
            self.model_combo.clear()
            if available_models:
                self.model_combo.addItems(available_models)
                if hasattr(self, 'results_text'):
                    self.log_message(f" {len(available_models)} modelo(s) carregado(s): {', '.join(available_models)}")
            else:
                self.model_combo.addItem('(nenhum modelo encontrado)')
                if hasattr(self, 'results_text'):
                    self.log_message(f' Nenhum modelo encontrado para {model_type}')
        except Exception as e:
            if hasattr(self, 'results_text'):
                self.log_message(f' Erro ao carregar modelos: {e}')

    def perform_inspection(self):
        ui_text = self.inspection_type_combo.currentText()
        idx = self.inspection_type_combo.currentIndex()
        map_types = {0: 'segmentation', 1: 'classification'}
        inspection_type = map_types.get(idx, 'classification')
        self._inspect_after_capture = inspection_type
        self.log_message(' Capturando imagem para inspeção...')
        self.inspection_capture_thread = CaptureThread(self.core)
        self.inspection_capture_thread.image_captured.connect(self._on_inspection_capture_completed)
        self.inspection_capture_thread.error_occurred.connect(self._on_inspection_capture_error)
        self.inspection_capture_thread.start()

    def _start_inspection(self, inspection_type: str, ui_text: str):
        self.inspect_btn.setEnabled(False)
        self.status_label.setText(f' {ui_text}...')
        model_name = self.model_combo.currentText()
        if not model_name or 'nenhum modelo' in model_name.lower():
            QMessageBox.warning(self, 'Erro', 'Nenhum modelo disponível!')
            self.inspect_btn.setEnabled(True)
            return
        self.inspection_thread = InspectionThread(self.core, inspection_type, self.inspection_image, model_name=model_name)
        self.inspection_thread.inspection_completed.connect(self.on_inspection_completed)
        self.inspection_thread.error_occurred.connect(self.on_inspection_error)
        self.inspection_thread.start()

    def _on_inspection_capture_completed(self, result: dict):
        raw = result.get('image')
        self.inspection_raw_image = raw
        image = raw
        if self.crop_enabled and self.crop_bbox:
            try:
                ops = [{'name': 'crop', 'bbox': self.crop_bbox}]
                image = self.core.preprocess_image(raw, ops)
            except Exception as e:
                self.log_message(f' Falha ao aplicar crop: {e}')
        self.inspection_image = image
        if getattr(self, '_inspect_after_capture', None):
            try:
                inspection_type = self._inspect_after_capture
                ui_text = 'Segmentação' if inspection_type == 'segmentation' else 'Classificação'
                self._inspect_after_capture = None
                QTimer.singleShot(50, lambda: self._start_inspection(inspection_type, ui_text))
            except Exception as e:
                self.log_message(f' Falha ao iniciar inspeção após captura: {e}')

    def _on_inspection_capture_error(self, error_msg: str):
        log.error(f'Erro na captura para inspeção: {error_msg}')
        QMessageBox.warning(self, 'Erro na Captura para Inspeção', f'Falha ao capturar imagem:\n{error_msg}')
        self.log_message(f' Erro na captura para inspeção: {error_msg}')

    @pyqtSlot(dict, str)
    @pyqtSlot(dict, str)
    def on_inspection_completed(self, result: dict, inspection_type: str):
        self.inspect_btn.setEnabled(True)
        self.status_label.setText(' Pronto')
        self.copy_results_btn.setEnabled(True)
        self.export_image_btn.setEnabled(True)
        self.vp_btn.setEnabled(True)
        self.vn_btn.setEnabled(True)
        self.fp_btn.setEnabled(True)
        self.fn_btn.setEnabled(True)
        self.current_results = result
        self.log_message(f' {inspection_type.capitalize()} completada')
        self.inspection_results_panel.display_results(self.inspection_image, result, inspection_type)
        if self.auto_save_check.isChecked():
            self.save_results()

    @pyqtSlot(str)
    def on_inspection_error(self, error_msg: str):
        self.inspect_btn.setEnabled(True)
        self.status_label.setText(' Erro')
        log.error(f'Erro na inspeção: {error_msg}')
        QMessageBox.warning(self, 'Erro na Inspeção', f'Falha na inspeção:\n{error_msg}')
        self.log_message(f' Erro na inspeção: {error_msg}')

    def save_results(self):
        self.log_message(' Iniciando salvamento de resultados...')
        if self.current_results is None or self.inspection_image is None:
            msg = 'Sem Dados: Não há resultados para salvar!'
            self.log_message(f' {msg}')
            QMessageBox.warning(self, 'Sem Dados', msg)
            return
        try:
            inspection_type_text = self.inspection_type_combo.currentText()
            inspection_type = 'classification' if 'Classificação' in inspection_type_text else 'segmentation'
            self.log_message(f' Tipo de inspeção: {inspection_type_text} ({inspection_type})')
            inspection_data = {'inspection_type': inspection_type, 'timestamp': datetime.now().isoformat(), 'image': self.inspection_image, 'results': self.current_results}
            self.log_message(f' Dados preparados para salvamento')
            ui_type = self.inspection_type_combo.currentText()
            map_types = {'Segmentação': 'segmentation', 'Classificação': 'classification'}
            inspection_type = map_types.get(ui_type, ui_type.lower())
            model_text = self.model_combo.currentText().strip()
            if not model_text or model_text.startswith('('):
                model_text = 'unknown_model'
            model_name = model_text.replace(' ', '_')
            self.log_message(f' Modelo: {model_name}')
            dest_base = Path.cwd() / 'data' / inspection_type / model_name / 'results'
            self.log_message(f' Diretório de destino: {dest_base}')
            dest_base.mkdir(parents=True, exist_ok=True)
            old_results_dir = getattr(self.core, 'results_dir', None)
            saved_path = None
            try:
                self.core.results_dir = dest_base
                self.log_message(f' Chamando core.save_inspection()...')
                saved_path = self.core.save_inspection(inspection_data)
                self.log_message(f' Inspeção salva em: {saved_path}')
                if saved_path:
                    try:
                        annotated = self.inspection_results_panel.annotated_image
                        if annotated is not None:
                            annotated_path = Path(saved_path) / 'annotated.jpg'
                            cv2.imwrite(str(annotated_path), annotated)
                            self.log_message(f' Imagem anotada salva: {annotated_path}')
                        else:
                            self.log_message(' Imagem anotada não disponível')
                    except Exception as e:
                        log.error(f' Erro ao salvar annotated.jpg: {e}')
                        self.log_message(f' Erro ao salvar annotated.jpg: {e}')
            finally:
                if old_results_dir is not None:
                    self.core.results_dir = old_results_dir
            if saved_path:
                self.inspection_results_panel.display_results(self.inspection_image, self.current_results, inspection_type)
                self.log_message(f' Resultados salvos: {saved_path}')
                self.load_history()
            else:
                QMessageBox.warning(self, 'Erro', 'Não foi possível salvar resultados')
        except Exception as e:
            error_msg = f'{type(e).__name__}: {str(e)}'
            log.exception(f' ERRO DETALHADO ao salvar: {error_msg}')
            self.log_message(f' ERRO ao salvar: {error_msg}')
            QMessageBox.critical(self, ' Erro ao Salvar Resultados', f'Falha ao salvar:\n\n{error_msg}')

    def clear_results(self):
        self.current_image = None
        self.current_results = None
        self.image_label.clear()
        self.image_label.setText('Imagem aparecerá aqui')
        self.image_info_label.setText('Sem imagem')
        self.results_text.clear()
        self.defects_table.setRowCount(0)
        self.inspect_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.log_message(' Resultados limpos')

    def _clear_inspection_results(self):
        self.inspection_image = None
        self.inspection_raw_image = None
        self.current_results = None
        self.inspection_results_panel.clear_results()
        self.inspect_btn.setEnabled(True)
        self.copy_results_btn.setEnabled(False)
        self.export_image_btn.setEnabled(False)
        self.vp_btn.setEnabled(False)
        self.vn_btn.setEnabled(False)
        self.fp_btn.setEnabled(False)
        self.fn_btn.setEnabled(False)
        self.log_message(' Resultados de inspeção limpos')

    def _copy_inspection_results(self):
        if self.current_results is None:
            QMessageBox.warning(self, 'Sem Dados', 'Não há resultados para copiar!')
            return
        try:
            inspection_type = self.inspection_type_combo.currentText()
            result_text = f'=== RESULTADO DA INSPEÇÃO ===\n'
            result_text += f'Tipo: {inspection_type}\n'
            result_text += f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
            result_text += f'\nDados:\n'
            for key, value in self.current_results.items():
                result_text += f'  {key}: {value}\n'
            clipboard = QApplication.clipboard()
            clipboard.setText(result_text)
            self.log_message(' Resultados copiados para a área de transferência')
            QMessageBox.information(self, 'Sucesso', 'Resultados copiados para a área de transferência!')
        except Exception as e:
            QMessageBox.critical(self, 'Erro', f'Falha ao copiar:\n{str(e)}')
            self.log_message(f' Erro ao copiar: {e}')

    def _export_inspection_image(self):
        if self.inspection_results_panel.annotated_image is None:
            QMessageBox.warning(self, 'Sem Dados', 'Não há imagem para exportar!')
            return
        try:
            file_path, _ = QFileDialog.getSaveFileName(self, 'Salvar Imagem da Inspeção', '', 'Imagem PNG (*.png);;Imagem JPEG (*.jpg);;Todas as imagens (*.png *.jpg *.bmp)')
            if not file_path:
                return
            cv2.imwrite(file_path, self.inspection_results_panel.annotated_image)
            self.log_message(f' Imagem exportada: {file_path}')
            QMessageBox.information(self, 'Sucesso', f'Imagem salva em:\n{file_path}')
        except Exception as e:
            QMessageBox.critical(self, 'Erro', f'Falha ao exportar:\n{str(e)}')
            self.log_message(f' Erro ao exportar: {e}')

    def _save_categoria(self, categoria: str):
        if self.inspection_image is None or self.current_results is None:
            QMessageBox.warning(self, 'Sem Dados', 'Realize uma inspeção antes de categorizar!')
            return
        try:
            ui_type = self.inspection_type_combo.currentText()
            map_types = {'Segmentação': 'segmentation', 'Classificação': 'classification'}
            inspection_type = map_types.get(ui_type, ui_type.lower())
            model_text = self.model_combo.currentText().strip()
            if not model_text or model_text.startswith('('):
                model_text = 'unknown_model'
            model_name = model_text.replace(' ', '_')
            base = Path.cwd() / 'data' / inspection_type / model_name / categoria
            base.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            folder = base / timestamp
            folder.mkdir(exist_ok=True)
            orig_file = folder / 'original.jpg'
            cv2.imwrite(str(orig_file), self.inspection_image)
            annotated = self.inspection_results_panel.annotated_image
            if annotated is not None:
                annot_file = folder / 'annotated.jpg'
                cv2.imwrite(str(annot_file), annotated)
            data = {'inspection_type': self.inspection_type_combo.currentText(), 'results': self.current_results, 'timestamp': timestamp}
            with open(folder / 'inspection_data.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.log_message(f" Categoria '{categoria}' salva em: {folder}")
            QMessageBox.information(self, 'Sucesso', f'Imagens e dados salvos em:\n{folder}')
        except Exception as e:
            QMessageBox.critical(self, 'Erro', f'Falha ao salvar categoria {categoria}:\n{e}')
            self.log_message(f' Erro ao salvar categoria {categoria}: {e}')

    def load_history(self):
        self.history_table.setRowCount(0)
        try:
            type_filter = self.history_type_combo.currentText()
            model_filter = self.history_model_combo.currentText()
            if type_filter not in ('Todos', 'Segmentação', 'Classificação'):
                type_filter = 'Todos'
            if model_filter in ('', 'Carregando...', '-- Nenhum --'):
                model_filter = ''
            data_dir = Path.cwd() / 'data'
            all_results = []
            if not data_dir.exists():
                self.log_message(" Pasta 'data' não encontrada")
                return
            type_mapping = {'Segmentação': 'segmentation', 'Classificação': 'classification'}
            if type_filter == 'Todos':
                types_to_search = ['segmentation', 'classification']
            else:
                types_to_search = [type_mapping.get(type_filter, type_filter.lower())]
            for type_folder in data_dir.iterdir():
                if not type_folder.is_dir():
                    continue
                type_name = type_folder.name
                if type_name not in types_to_search and type_filter != 'Todos':
                    continue
                for model_folder in type_folder.iterdir():
                    if not model_folder.is_dir():
                        continue
                    model_name = model_folder.name
                    if model_filter != 'Todos':
                        if model_filter.lower() not in model_name.lower():
                            continue
                    results_dir = model_folder / 'results'
                    if results_dir.exists():
                        for timestamp_dir in results_dir.iterdir():
                            if timestamp_dir.is_dir():
                                json_file = timestamp_dir / 'inspection_data.json'
                                if json_file.exists():
                                    all_results.append((json_file, timestamp_dir, type_name, model_name))
                    for category_folder in model_folder.iterdir():
                        if not category_folder.is_dir() or category_folder.name == 'results':
                            continue
                        for timestamp_dir in category_folder.iterdir():
                            if timestamp_dir.is_dir():
                                json_file = timestamp_dir / 'inspection_data.json'
                                if json_file.exists():
                                    all_results.append((json_file, timestamp_dir, type_name, model_name))
            if not all_results:
                self.log_message(' Nenhuma inspeção encontrada com os filtros selecionados')
                return
            all_results.sort(key=lambda x: x[1].name, reverse=True)
            self.history_result_dirs = [entry[1] for entry in all_results]
            self._update_available_models(type_filter)
            self.history_table.setRowCount(len(all_results))
            for row, (json_file, result_dir, type_name, model_name) in enumerate(all_results):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    timestamp_str = data.get('timestamp', result_dir.name)
                    results = data.get('results', {})
                    try:
                        dt = datetime.fromisoformat(timestamp_str)
                        timestamp_display = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        timestamp_display = timestamp_str
                    type_display = 'Classificação' if type_name == 'classification' else 'Segmentação'
                    if type_name == 'classification':
                        status = results.get('status', 'unknown')
                        if status == 'indeterminado':
                            result_text = ' INDETERMINADO'
                        elif results.get('defects_detected'):
                            result_text = ' RUIM'
                        else:
                            result_text = ' BOA'
                        defect_count = '1' if results.get('defects_info') else '0'
                    else:
                        total_defects = results.get('total_defects', 0)
                        if total_defects > 0:
                            result_text = f'  {total_defects} defeito(s)'
                        else:
                            result_text = ' SEM DEFEITOS'
                        defect_count = str(total_defects)
                    self.history_table.setItem(row, 0, QTableWidgetItem(timestamp_display))
                    self.history_table.setItem(row, 1, QTableWidgetItem(type_display))
                    self.history_table.setItem(row, 2, QTableWidgetItem(model_name))
                    self.history_table.setItem(row, 3, QTableWidgetItem(result_text))
                    self.history_table.setItem(row, 4, QTableWidgetItem(defect_count))
                    view_btn = QPushButton(' Ver')
                    view_btn.setMaximumWidth(80)
                    view_btn.clicked.connect(lambda checked, r=row: self._show_history_mask_image(r))
                    self.history_table.setCellWidget(row, 5, view_btn)
                except Exception as e:
                    log.debug(f'Erro ao carregar {json_file}: {e}')
                    continue
            self.log_message(f' Histórico carregado: {len(all_results)} inspeção(ões)')
        except Exception as e:
            self.log_message(f' Erro ao carregar histórico: {e}')

    def _history_row_double_clicked(self, row: int, column: int):
        try:
            if 0 <= row < len(self.history_result_dirs):
                folder = self.history_result_dirs[row]
                dlg = HistoryImageDialog(folder, self)
                dlg.exec_()
        except Exception as e:
            log.debug(f'Erro ao abrir diálogo de histórico: {e}')

    def _show_history_mask_image(self, row: int):
        try:
            if 0 <= row < len(self.history_result_dirs):
                folder = self.history_result_dirs[row]
                possible_filenames = ['annotated.jpg', 'image.jpg', 'original.jpg', 'mask.jpg']
                image_file = None
                for filename in possible_filenames:
                    candidate = folder / filename
                    if candidate.exists():
                        image_file = candidate
                        break
                if not image_file:
                    for jpg_file in folder.glob('*.jpg'):
                        image_file = jpg_file
                        break
                if not image_file:
                    json_file = folder / 'inspection_data.json'
                    if json_file.exists():
                        try:
                            with open(json_file, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            img_path_str = data.get('image_file', '')
                            if img_path_str:
                                img_file = folder / img_path_str.replace('\\', '/')
                                if img_file.exists():
                                    image_file = img_file
                        except Exception:
                            pass
                if image_file and image_file.exists():
                    dlg = QDialog(self)
                    dlg.setWindowTitle(f'Resultado da Análise - {folder.name}')
                    dlg.setMinimumSize(900, 700)
                    layout = QVBoxLayout()
                    title = QLabel(' Visualização do Resultado')
                    title.setStyleSheet('font-weight: bold; font-size: 14px; padding: 10px;')
                    layout.addWidget(title)
                    pix = QPixmap(str(image_file))
                    if pix.isNull():
                        layout.addWidget(QLabel(' Falha ao carregar a imagem'))
                    else:
                        img_label = QLabel()
                        img_label.setAlignment(Qt.AlignCenter)
                        img_label.setPixmap(pix.scaledToWidth(850, Qt.SmoothTransformation))
                        scroll = QScrollArea()
                        scroll.setWidgetResizable(True)
                        scroll.setWidget(img_label)
                        layout.addWidget(scroll, 1)
                    info = QLabel(f' Arquivo: {image_file.name}')
                    info.setStyleSheet('font-size: 10px; color: #888; padding: 5px;')
                    layout.addWidget(info)
                    close_btn = QPushButton('Fechar')
                    close_btn.clicked.connect(dlg.accept)
                    layout.addWidget(close_btn)
                    dlg.setLayout(layout)
                    dlg.exec_()
                else:
                    search_paths = '\n'.join([str(folder / f) for f in possible_filenames[:3]])
                    QMessageBox.warning(self, 'Aviso', f'Nenhuma imagem encontrada para este resultado.\n\nPastas procuradas:\n{search_paths}\n\n Caminho: {folder}')
        except Exception as e:
            log.error(f'Erro ao abrir imagem: {e}', exc_info=True)
            QMessageBox.critical(self, 'Erro', f'Erro ao abrir imagem: {e}')

    def _update_available_models(self, type_filter):
        try:
            was_blocked = self.history_model_combo.signalsBlocked()
            data_dir = Path.cwd() / 'data'
            models = set()
            if not data_dir.exists():
                return
            type_mapping = {'Segmentação': 'segmentation', 'Classificação': 'classification'}
            if type_filter == 'Todos':
                types_to_search = ['segmentation', 'classification']
            else:
                types_to_search = [type_mapping.get(type_filter, type_filter.lower())]
            for type_folder in data_dir.iterdir():
                if not type_folder.is_dir() or type_folder.name not in types_to_search:
                    continue
                for model_folder in type_folder.iterdir():
                    if model_folder.is_dir():
                        models.add(model_folder.name)
            current_model = self.history_model_combo.currentText()
            self.history_model_combo.blockSignals(True)
            self.history_model_combo.clear()
            self.history_model_combo.addItem('Todos')
            for model in sorted(models):
                self.history_model_combo.addItem(model)
            idx = self.history_model_combo.findText(current_model, Qt.MatchExactly)
            if idx >= 0:
                self.history_model_combo.setCurrentIndex(idx)
            else:
                self.history_model_combo.setEditText(current_model)
            self.history_model_combo.blockSignals(was_blocked)
        except Exception as e:
            log.debug(f'Erro ao atualizar modelos: {e}')

    def view_history_item(self, row: int, result_dir: Path):
        try:
            json_file = result_dir / 'inspection_data.json'
            if not json_file.exists():
                QMessageBox.warning(self, 'Erro', 'Arquivo de inspeção não encontrado')
                return
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            image_data = data.get('image')
            results = data.get('results', {})
            inspection_type = data.get('inspection_type', 'segmentation')
            if isinstance(image_data, list):
                image = np.array(image_data, dtype=np.uint8)
            else:
                image = None
            if image is not None:
                self.inspection_results_panel.display_results(image, results, inspection_type)
                self.log_message(f' Visualizando: {inspection_type}')
            else:
                result_text = self._format_result_text(results, inspection_type)
                QMessageBox.information(self, 'Resultado da Inspeção', result_text)
        except Exception as e:
            QMessageBox.critical(self, 'Erro', f'Erro ao carregar inspeção:\n{str(e)}')
            self.log_message(f' Erro ao visualizar: {e}')

    def _format_result_text(self, results: dict, inspection_type: str) -> str:
        if inspection_type == 'classification':
            status = results.get('status', 'unknown')
            defects_info = results.get('defects_info', [])
            if status == 'indeterminado':
                text = ' CLASSIFICAÇÃO INDETERMINADA\n\n'
                text += 'Confiança abaixo do limite.\n'
                text += 'Recomenda-se nova captura.'
            elif results.get('defects_detected'):
                text = ' FRUTA RUIM\n\n'
                if defects_info:
                    defect = defects_info[0]
                    text += f"Classe: {defect.get('class', 'N/A')}\n"
                    text += f"Confiança: {defect.get('confidence', 0):.1%}"
            else:
                text = ' FRUTA BOA\n\n'
                if defects_info:
                    defect = defects_info[0]
                    text += f"Classe: {defect.get('class', 'N/A')}\n"
                    text += f"Confiança: {defect.get('confidence', 0):.1%}"
        else:
            total = results.get('total_defects', 0)
            has_defects = results.get('has_defects', False)
            if has_defects:
                text = f'  {total} DEFEITO(S) ENCONTRADO(S)\n\n'
                defects = results.get('defects', [])
                for defect in defects[:5]:
                    text += f"• {defect.get('class_name', 'N/A')}: {defect.get('confidence', 0):.1%}\n"
            else:
                text = ' NENHUM DEFEITO ENCONTRADO'
        return text

    def export_history(self):
        try:
            if self.history_table.rowCount() == 0:
                QMessageBox.warning(self, 'Aviso', 'Nenhum resultado para exportar')
                return
            file_path, _ = QFileDialog.getSaveFileName(self, 'Salvar histórico como CSV', str(Path.cwd() / 'historico.csv'), 'CSV Files (*.csv)')
            if not file_path:
                return
            import csv
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                headers = []
                for col in range(self.history_table.columnCount()):
                    headers.append(self.history_table.horizontalHeaderItem(col).text())
                writer.writerow(headers)
                for row in range(self.history_table.rowCount()):
                    row_data = []
                    for col in range(self.history_table.columnCount()):
                        item = self.history_table.item(row, col)
                        if item:
                            row_data.append(item.text())
                        else:
                            row_data.append('')
                    writer.writerow(row_data)
            QMessageBox.information(self, 'Sucesso', f'Histórico exportado para:\n{file_path}')
            self.log_message(f' Histórico exportado: {file_path}')
        except Exception as e:
            QMessageBox.critical(self, 'Erro', f'Falha ao exportar histórico:\n{e}')
            self.log_message(f' Erro ao exportar: {e}')

    def reload_camera(self):
        try:
            current_index = self.core.camera_manager._current_index if self.core.camera_manager else -1
            if current_index < 0:
                self.log_message('  Nenhuma câmera ativa para recarregar')
                return
            self.log_message(' Recarregando câmera...')
            if self.core.switch_camera(current_index):
                self.log_message(' Câmera recarregada com sucesso')
                QTimer.singleShot(300, self.update_camera_info)
                QTimer.singleShot(500, self._update_camera_combo)
            else:
                self.log_message(' Falha ao recarregar câmera')
                QTimer.singleShot(100, self._update_camera_combo)
        except Exception as e:
            self.log_message(f' Erro ao recarregar câmera: {e}')
            log.error(f'Erro em reload_camera: {e}')

    def _reload_profiles_list(self):
        try:
            camera_info = self.core.get_system_info().get('camera', {})
            camera_type = camera_info.get('type', 'unknown')
            profiles = self.profile_manager.list_profiles(camera_type)
            self.profile_combo.blockSignals(True)
            self.profile_combo.clear()
            if profiles:
                self.profile_combo.addItems(profiles)
                self.profile_combo.insertItem(0, '-- Selecione um perfil --')
                self.profile_combo.setCurrentIndex(0)
            else:
                self.profile_combo.addItem('-- Nenhum perfil --')
            self.profile_combo.blockSignals(False)
            self.log_message(f' {len(profiles)} perfil(is) carregado(s)')
        except Exception as e:
            self.log_message(f' Erro ao recarregar perfis: {e}')

    def _on_profile_selected(self, index: int):
        log.debug(f'_on_profile_selected chamado com index={index}')
        profile_name = self.profile_combo.currentText()
        if not profile_name or profile_name.startswith('--'):
            return
        try:
            success = self.capture_mgr.apply_profile(profile_name)
            if success:
                QMessageBox.information(self, 'Perfil Aplicado', f"Perfil '{profile_name}' aplicado à câmera.")
                self.log_message(f' Perfil aplicado: {profile_name}')
            else:
                QMessageBox.warning(self, 'Falha', f"Não foi possível aplicar perfil '{profile_name}'")
                self.log_message(f' Falha ao aplicar perfil: {profile_name}')
        except Exception as e:
            log.error(f"Erro ao aplicar perfil '{profile_name}': {e}")
            QMessageBox.critical(self, 'Erro', f'Erro ao aplicar perfil: {e}')

    def _create_new_profile(self):
        try:
            dialog = CreateProfileDialog(parent=self)
            if dialog.exec_() == QDialog.Accepted:
                profile_name = dialog.get_profile_name()
                if not profile_name:
                    QMessageBox.warning(self, 'Erro', 'Nome do perfil não pode estar vazio')
                    return
                if self.profile_manager.profile_exists(profile_name):
                    QMessageBox.warning(self, 'Erro', f"Perfil '{profile_name}' já existe")
                    return
                camera_info = self.core.get_system_info().get('camera', {})
                camera_type = camera_info.get('type', 'unknown')
                params = {}
                try:
                    camera_obj = None
                    if hasattr(self.core, 'camera_manager'):
                        if hasattr(self.core.camera_manager, 'camera'):
                            camera_obj = self.core.camera_manager.camera
                        elif hasattr(self.core.camera_manager, 'current_camera'):
                            camera_obj = self.core.camera_manager.current_camera
                    if camera_obj:
                        params = camera_obj.get_parameters()
                except Exception as e:
                    log.warning(f'Aviso ao obter parâmetros para perfil: {e}')
                if self.profile_manager.create_profile(profile_name, camera_type, params):
                    QMessageBox.information(self, 'Sucesso', f"Perfil '{profile_name}' criado!")
                    self.log_message(f' Perfil criado: {profile_name}')
                    self._reload_profiles_list()
                else:
                    QMessageBox.critical(self, 'Erro', 'Não foi possível criar o perfil')
        except Exception as e:
            QMessageBox.critical(self, 'Erro', f'Erro ao criar perfil: {e}')

    def _load_selected_profile(self):
        try:
            profile_name = self.profile_combo.currentText()
            if not profile_name or profile_name.startswith('--'):
                QMessageBox.warning(self, 'Erro', 'Selecione um perfil para carregar')
                return
            profile_data = self.profile_manager.load_profile(profile_name)
            if not profile_data:
                QMessageBox.critical(self, 'Erro', f"Não foi possível carregar perfil '{profile_name}'")
                return
            params = profile_data.get('parameters', {})
            success_count = 0
            camera_obj = None
            if hasattr(self.core, 'camera_manager'):
                if hasattr(self.core.camera_manager, 'camera'):
                    camera_obj = self.core.camera_manager.camera
                elif hasattr(self.core.camera_manager, 'current_camera'):
                    camera_obj = self.core.camera_manager.current_camera
            if camera_obj:
                for param_name, param_value in params.items():
                    try:
                        if camera_obj.set_parameter(param_name, param_value):
                            success_count += 1
                    except Exception as e:
                        log.debug(f'Erro ao aplicar {param_name}: {e}')
            self._update_camera_combo()
            QMessageBox.information(self, 'Sucesso', f"Perfil '{profile_name}' carregado!\n{success_count} parâmetro(s) aplicado(s)")
            self.log_message(f' Perfil carregado: {profile_name}')
        except Exception as e:
            QMessageBox.critical(self, 'Erro', f'Erro ao carregar perfil: {e}')

    def _save_current_profile(self):
        try:
            profile_name = self.profile_combo.currentText()
            if not profile_name or profile_name.startswith('--'):
                self._create_new_profile()
                return
            camera_info = self.core.get_system_info().get('camera', {})
            camera_type = camera_info.get('type', 'unknown')
            params = {}
            try:
                camera_obj = None
                if hasattr(self.core, 'camera_manager') and self.core.camera_manager:
                    camera_obj = self.core.camera_manager.active_camera
                if camera_obj:
                    params = camera_obj.get_parameters()
            except Exception as e:
                log.warning(f'Aviso ao obter parâmetros para salvar: {e}')
            self.profile_manager.delete_profile(profile_name)
            if self.profile_manager.create_profile(profile_name, camera_type, params):
                QMessageBox.information(self, 'Sucesso', f"Perfil '{profile_name}' salvo!")
                self.log_message(f' Perfil salvo: {profile_name}')
            else:
                QMessageBox.critical(self, 'Erro', 'Não foi possível salvar o perfil')
        except Exception as e:
            QMessageBox.critical(self, 'Erro', f'Erro ao salvar perfil: {e}')

    def _delete_selected_profile(self):
        try:
            profile_name = self.profile_combo.currentText()
            if not profile_name or profile_name.startswith('--'):
                QMessageBox.warning(self, 'Erro', 'Selecione um perfil para deletar')
                return
            reply = QMessageBox.question(self, 'Confirmar Deleção', f"Tem certeza que deseja deletar o perfil '{profile_name}'?\n\nEsta ação não pode ser desfeita.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                if self.profile_manager.delete_profile(profile_name):
                    QMessageBox.information(self, 'Sucesso', f"Perfil '{profile_name}' deletado!")
                    self.log_message(f' Perfil deletado: {profile_name}')
                    self._reload_profiles_list()
                else:
                    QMessageBox.critical(self, 'Erro', 'Não foi possível deletar o perfil')
        except Exception as e:
            QMessageBox.critical(self, 'Erro', f'Erro ao deletar perfil: {e}')

    def load_pfs_file(self):
        try:
            file_path, _ = QFileDialog.getOpenFileName(self, 'Selecionar arquivo .pfs', '', 'Arquivos .pfs (*.pfs)')
            if not file_path:
                return
            profile_name = Path(file_path).stem
            success = self.pfs_mgr.load_pfs_profile(Path(file_path), profile_name)
            if success:
                QMessageBox.information(self, 'Sucesso', f"Arquivo .pfs carregado como perfil '{profile_name}'!")
                self.log_message(f' Arquivo .pfs carregado: {file_path}')
                self.refresh_pfs_list()
                applied = False
                try:
                    applied = self.capture_mgr.apply_profile(profile_name)
                except Exception as e:
                    log.error(f'Erro ao aplicar perfil recém-carregado: {e}')
                if applied:
                    self.log_message(f" Perfil .pfs '{profile_name}' aplicado após carregamento")
                else:
                    self.log_message(f" Falha ao aplicar perfil .pfs '{profile_name}'")
            else:
                QMessageBox.critical(self, 'Erro', 'Não foi possível carregar o arquivo .pfs')
        except Exception as e:
            QMessageBox.critical(self, 'Erro', f'Erro ao carregar arquivo .pfs: {e}')

    def save_pfs_file(self):
        try:
            current_profile = self.pfs_profile_combo.currentText()
            if not current_profile:
                QMessageBox.warning(self, 'Aviso', 'Selecione um perfil para salvar')
                return
            file_path, _ = QFileDialog.getSaveFileName(self, 'Salvar arquivo .pfs', f'{current_profile}.pfs', 'Arquivos .pfs (*.pfs)')
            if not file_path:
                return
            success = self.pfs_mgr.save_pfs_profile(current_profile, Path(file_path))
            if success:
                QMessageBox.information(self, 'Sucesso', f'Perfil salvo como .pfs: {file_path}')
                self.log_message(f' Perfil salvo como .pfs: {file_path}')
            else:
                QMessageBox.critical(self, 'Erro', 'Não foi possível salvar o arquivo .pfs')
        except Exception as e:
            QMessageBox.critical(self, 'Erro', f'Erro ao salvar arquivo .pfs: {e}')

    def refresh_pfs_list(self):
        try:
            self.pfs_profile_combo.clear()
            pfs_profiles = self.pfs_mgr.list_pfs_profiles()
            if pfs_profiles:
                self.pfs_profile_combo.addItems(pfs_profiles)
                self.log_message(f' Lista de perfis .pfs atualizada: {len(pfs_profiles)} perfis')
            else:
                self.pfs_profile_combo.addItem('Nenhum perfil .pfs encontrado')
                self.log_message(' Nenhum perfil .pfs encontrado')
            self.pfs_params_table.setRowCount(0)
            self.pfs_info_text.clear()
        except Exception as e:
            QMessageBox.critical(self, 'Erro', f'Erro ao atualizar lista de perfis: {e}')

    def on_pfs_profile_selected(self, profile_name: str):
        if not profile_name or profile_name == 'Nenhum perfil .pfs encontrado':
            self.pfs_params_table.setRowCount(0)
            self.pfs_info_text.clear()
            return
        try:
            profile_data = self.pfs_mgr.load_profile(profile_name)
            if not profile_data:
                return
            self._populate_pfs_params_table(profile_data)
            self._populate_pfs_info(profile_data)
            self.log_message(f' Perfil .pfs selecionado: {profile_name}')
            applied = False
            try:
                applied = self.capture_mgr.apply_profile(profile_name)
            except Exception as e:
                log.error(f'Erro ao aplicar perfil .pfs: {e}')
            if applied:
                self.log_message(f' Perfil .pfs aplicado: {profile_name}')
            else:
                self.log_message(f' Falha ao aplicar perfil .pfs: {profile_name}')
        except Exception as e:
            QMessageBox.critical(self, 'Erro', f'Erro ao carregar perfil: {e}')

    def delete_pfs_profile(self):
        try:
            current_profile = self.pfs_profile_combo.currentText()
            if not current_profile or current_profile == 'Nenhum perfil .pfs encontrado':
                QMessageBox.warning(self, 'Aviso', 'Selecione um perfil para excluir')
                return
            reply = QMessageBox.question(self, 'Confirmar Exclusão', f"Tem certeza que deseja excluir o perfil '{current_profile}'?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                profile_path = self.pfs_mgr.profiles_dir / f'{current_profile}.json'
                if profile_path.exists():
                    profile_path.unlink()
                QMessageBox.information(self, 'Sucesso', f"Perfil '{current_profile}' excluído!")
                self.log_message(f' Perfil .pfs excluído: {current_profile}')
                self.refresh_pfs_list()
        except Exception as e:
            QMessageBox.critical(self, 'Erro', f'Erro ao excluir perfil: {e}')

    def _populate_pfs_params_table(self, profile_data: dict):
        try:
            params = profile_data.get('parameters', {})
            camera_params = {}
            for key, value in params.items():
                if key not in ['format', 'metadata', 'file_info', 'converted_at']:
                    camera_params[key] = value
            self.pfs_params_table.setRowCount(len(camera_params))
            for row, (param_name, param_value) in enumerate(camera_params.items()):
                self.pfs_params_table.setItem(row, 0, QTableWidgetItem(param_name))
                value_item = QTableWidgetItem(str(param_value))
                self.pfs_params_table.setItem(row, 1, value_item)
                edit_btn = QPushButton(' Editar')
                edit_btn.clicked.connect(lambda checked, p=param_name, v=str(param_value): self._edit_pfs_parameter(p, v))
                self.pfs_params_table.setCellWidget(row, 2, edit_btn)
            self.pfs_params_table.resizeColumnsToContents()
        except Exception as e:
            log.error(f'Erro ao popular tabela de parâmetros: {e}')

    def _populate_pfs_info(self, profile_data: dict):
        try:
            info_text = f' Informações do Perfil\n\n'
            info_text += f"Nome: {profile_data.get('name', 'N/A')}\n"
            info_text += f"Tipo: {profile_data.get('camera_type', 'N/A')}\n"
            info_text += f"Criado em: {profile_data.get('created_at', 'N/A')}\n"
            info_text += f"Última modificação: {profile_data.get('timestamp', 'N/A')}\n\n"
            params = profile_data.get('parameters', {})
            if 'format' in params and params['format'] == 'pfs':
                info_text += f' Formato: Arquivo .pfs convertido\n'
                if 'converted_at' in params:
                    info_text += f" Convertido em: {params['converted_at']}\n"
                if 'metadata' in params:
                    metadata = params['metadata']
                    if 'device' in metadata:
                        info_text += f" Dispositivo: {metadata['device']}\n"
                    if 'genapi_version' in metadata:
                        info_text += f" GenAPI: {metadata['genapi_version']}\n"
            camera_params = sum((1 for k, v in params.items() if k not in ['format', 'metadata', 'file_info', 'converted_at']))
            info_text += f' Parâmetros: {camera_params}\n'
            self.pfs_info_text.setPlainText(info_text)
        except Exception as e:
            log.error(f'Erro ao popular informações do perfil: {e}')

    def _edit_pfs_parameter(self, param_name: str, current_value: str):
        try:
            current_profile = self.pfs_profile_combo.currentText()
            if not current_profile:
                return
            new_value, ok = QInputDialog.getText(self, 'Editar Parâmetro', f"Novo valor para '{param_name}':", text=current_value)
            if ok and new_value != current_value:
                success = self.pfs_mgr.modify_pfs_parameter(current_profile, param_name, new_value)
                if success:
                    QMessageBox.information(self, 'Sucesso', f"Parâmetro '{param_name}' modificado!")
                    self.log_message(f' Parâmetro modificado: {param_name} = {new_value}')
                    self.on_pfs_profile_selected(current_profile)
                else:
                    QMessageBox.critical(self, 'Erro', 'Não foi possível modificar o parâmetro')
        except Exception as e:
            QMessageBox.critical(self, 'Erro', f'Erro ao editar parâmetro: {e}')

    def reload_models(self):
        log.debug('reload_models chamado na interface')
        try:
            new_threshold = self.confidence_spin.value()
            log.debug(f'Novo threshold obtido: {new_threshold}')
            config_updated = self.core.update_model_configs(segmentation_threshold=new_threshold, classification_threshold=new_threshold)
            models_reloaded = self.core.reload_models(force_reload=True)
            messages = []
            if config_updated:
                messages.append(f' Threshold atualizado para {new_threshold:.3f}')
            if models_reloaded:
                messages.append(' Modelos recarregados do disco')
            if messages:
                result_msg = '\n'.join(messages)
                QMessageBox.information(self, 'Recarregar Modelos', result_msg)
                self.log_message(f' Modelos atualizados: threshold={new_threshold:.3f}')
            else:
                QMessageBox.warning(self, 'Recarregar Modelos', '  Nenhum modelo disponível para atualização')
                self.log_message('  Nenhum modelo disponível para recarregar')
        except Exception as e:
            QMessageBox.critical(self, 'Erro', f'Falha ao recarregar modelos:\n{str(e)}')
            self.log_message(f' Erro ao recarregar modelos: {e}')

    def toggle_web_server(self):
        QMessageBox.information(self, 'Servidor Web', 'Funcionalidade será implementada.\nO servidor web permitirá acesso via navegador.')

    def show_log_window(self):
        if hasattr(self, 'logs_text') and self.logs_text is not None:
            log_text = self.logs_text.toPlainText()
            if not log_text:
                log_text = '(sem mensagens no log)'
        else:
            log_text = ' LOG DO SISTEMA\n\n(nenhum widget de log disponível)'
        QMessageBox.information(self, 'Log do Sistema', log_text)

    def log_message(self, message: str):
        timestamp = datetime.now().strftime('%H:%M:%S')
        if not hasattr(self, 'logs_text') or self.logs_text is None:
            return
        log_text = self.logs_text.toPlainText()
        log_text = f'[{timestamp}] {message}\n' + log_text
        lines = log_text.split('\n')
        if len(lines) > 500:
            log_text = '\n'.join(lines[:500])
        self.logs_text.setPlainText(log_text)

    def _clear_logs(self):
        if hasattr(self, 'logs_text') and self.logs_text is not None:
            self.logs_text.clear()
            self.log_message(' Logs limpos')

    def _export_logs(self):
        if not hasattr(self, 'logs_text') or self.logs_text is None:
            return
        filepath, _ = QFileDialog.getSaveFileName(self, 'Salvar logs', str(Path.cwd() / f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"), 'Arquivos de Texto (*.txt);;Todas (*.*);')
        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(self.logs_text.toPlainText())
                self.log_message(f' Logs exportados: {filepath}')
            except Exception as e:
                self.log_message(f' Erro ao exportar logs: {e}')

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.activateWindow()

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Sair', 'Deseja realmente sair?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if hasattr(self, 'streaming_popup') and self.streaming_popup:
                try:
                    self.streaming_popup.close()
                except Exception:
                    pass
                self.streaming_popup = None
            if self.streaming_thread:
                try:
                    self.streaming_thread.stop()
                except Exception:
                    pass
                self.streaming_thread = None
            if hasattr(self, 'capture_timer'):
                try:
                    self.capture_timer.stop()
                except Exception:
                    pass
            try:
                self.core.cleanup()
            except Exception:
                pass
            event.accept()
            QApplication.quit()
        else:
            event.ignore()

def start_desktop_app(core: SystemCore=None):
    QApplication.setAttribute(Qt.AA_UseSoftwareOpenGL)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)

    def _global_excepthook(exc_type, exc_value, exc_traceback):
        log.error(' Exceção não tratada', exc_info=(exc_type, exc_value, exc_traceback))
        try:
            QMessageBox.critical(None, 'Erro Inesperado', f'{exc_value}')
        except Exception:
            pass
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    sys.excepthook = _global_excepthook
    app = QApplication(sys.argv)
    app.setApplicationName('Sistema de Inspeção')
    app.setApplicationDisplayName('Sistema de Inspeção Híbrido')
    if core is None:
        try:
            core = SystemCore()
            if not core.initialize():
                log.error('Falha ao inicializar SystemCore')
                QMessageBox.critical(None, 'Erro de Inicialização', 'Não foi possível inicializar o sistema.')
                app.quit()
                return 1
        except Exception as e:
            log.error(f'Exceção ao criar/inicializar SystemCore: {e}', exc_info=True)
            QMessageBox.critical(None, 'Erro de Inicialização', f'Falha ao inicializar o sistema:\n{str(e)}')
            app.quit()
            return 1
    try:
        log.info('  Criando janela principal...')
        window = MainWindow(core)
        log.info('  Janela criada, chamando show()...')
        window.show()
        log.info('  window.show() retornou')
        log.info('  Interface desktop inicializada')

        def _handle_sigint(sig, frame):
            try:
                log.info(' SIGINT recebido. Enviando quit para QApplication...')
                QTimer.singleShot(0, app.quit)
            except Exception:
                pass
        signal.signal(signal.SIGINT, _handle_sigint)
        try:
            app.aboutToQuit.connect(lambda: core.cleanup())
        except Exception:
            pass
        try:
            ret = app.exec_()
            log.info(f'  QApplication.exec_ returned {ret}')
            return ret
        except Exception as e:
            log.error(f' Erro durante a execução da aplicação: {e}', exc_info=True)
            QMessageBox.critical(None, 'Erro Crítico', f'Erro ao executar a interface:\n{str(e)}')
            return 1
    except Exception as e:
        log.error(f' Erro ao inicializar desktop: {e}')
        QMessageBox.critical(None, 'Erro Crítico', f'Erro ao inicializar a interface:\n{str(e)}')
        core.cleanup()
        return 1