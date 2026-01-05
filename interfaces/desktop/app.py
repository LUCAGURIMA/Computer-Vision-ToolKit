"""
Interface desktop PyQt5.

Esta é a interface desktop do sistema.
Ela:
1. Cria janelas e widgets
2. Comunica com o SystemCore
3. Mostra resultados em tempo real
4. Permite controle local sem navegador
"""

import sys
import json
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QTabWidget, QGroupBox,
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QSystemTrayIcon, QMenu, QAction, QStyle,
    QDialog, QRubberBand, QLineEdit, QFileDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QTimer, QRect, QSize
from PyQt5.QtGui import QImage, QPixmap, QIcon, QFont
import cv2
import numpy as np
import time

from core.system_core import SystemCore
from core.utils.logger import log
from config import DESKTOP_CONFIG, ASSETS_DIR

# ============================================
# THREADS PARA OPERAÇÕES BLOQUEANTES
# ============================================

class CaptureThread(QThread):
    """Thread para captura de imagem (não trava a UI)"""
    
    # Sinais (signals) para comunicação com a thread principal
    image_captured = pyqtSignal(dict)      # Emite quando imagem é capturada
    error_occurred = pyqtSignal(str)       # Emite quando há erro
    
    def __init__(self, core: SystemCore):
        super().__init__()
        self.core = core
    
    def run(self):
        """Método executado na thread separada"""
        try:
            result = self.core.capture_image()
            if result and result.get("success"):
                self.image_captured.emit(result)
            else:
                self.error_occurred.emit("Falha na captura")
        except Exception as e:
            self.error_occurred.emit(str(e))


class CropDialog(QDialog):
    """Diálogo simples para selecionar uma região de crop numa imagem.

    Exemplo:
        dlg = CropDialog(image_numpy)
        if dlg.exec_() == QDialog.Accepted:
            bbox = dlg.bbox  # [x1,y1,x2,y2] em coordenadas da imagem original
    """
    def __init__(self, image: np.ndarray, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Selecionar Crop")
        self.image = image
        self.bbox = None

        # Converte para QPixmap e escala para caber na janela mantendo proporção
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

        # Limita tamanho de exibição para não ultrapassar a tela
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
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # Eventos do label
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
            # Mapeia coordenadas do display (label/pixmap escalado) para a imagem original
            display_pixmap = self.label.pixmap()
            if display_pixmap is None:
                return
            dp_w = display_pixmap.width()
            dp_h = display_pixmap.height()

            orig_h, orig_w = self.image.shape[:2]

            # fatores de escala entre imagem original e pixmap exibido
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

class InspectionThread(QThread):
    """Thread para execução de inspeções"""
    
    inspection_completed = pyqtSignal(dict, str)  # Resultado e tipo
    error_occurred = pyqtSignal(str)
    
    def __init__(self, core: SystemCore, inspection_type: str, image: np.ndarray = None):
        super().__init__()
        self.core = core
        self.inspection_type = inspection_type
        self.image = image
    
    def run(self):
        try:
            if self.inspection_type == "segmentation":
                result = self.core.perform_segmentation(self.image)
            elif self.inspection_type == "classification":
                result = self.core.perform_classification(self.image)
            else:
                raise ValueError(f"Tipo de inspeção inválido: {self.inspection_type}")
            
            self.inspection_completed.emit(result, self.inspection_type)
            
        except Exception as e:
            self.error_occurred.emit(str(e))

# ============================================
# JANELA PRINCIPAL
# ============================================

class MainWindow(QMainWindow):
    """Janela principal da aplicação desktop"""
    
    def __init__(self, core: SystemCore):
        super().__init__()
        self.core = core
        # Aba de Captura: visualização apenas
        self.current_image = None
        self.raw_image = None
        # Aba de Inspeção: fluxo independente
        self.inspection_image = None
        self.inspection_raw_image = None
        self.current_results = None
        # Crop settings
        self.crop_enabled = False
        self.crop_bbox = None  # [x1,y1,x2,y2]
        # Flag para executar inspeção logo após captura automática
        self._inspect_after_capture = None  # type: Optional[str]
        
        # Configurações da janela
        self.setWindowTitle(DESKTOP_CONFIG["window_title"])
        self.setGeometry(100, 100, *DESKTOP_CONFIG["window_size"])
        
        # Aplica tema
        self._apply_theme()
        
        # Cria interface
        self._create_ui()
        
        # Conecta callbacks do core
        self._connect_core_callbacks()
        
        # Sistema tray (bandeja do sistema)
        if DESKTOP_CONFIG["show_system_tray"]:
            self._create_system_tray()
        
        log.info("🖥️  Interface desktop inicializada")
    
    def _apply_theme(self):
        """Aplica tema escuro/claro"""
        theme = DESKTOP_CONFIG["theme"]
        
        if theme == "dark":
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QPushButton {
                    background-color: #3c3c3c;
                    color: white;
                    border: 1px solid #555;
                    padding: 8px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #4a4a4a;
                }
                QPushButton:pressed {
                    background-color: #2a2a2a;
                }
                QLabel {
                    color: #ffffff;
                }
                QTextEdit, QTableWidget {
                    background-color: #1e1e1e;
                    color: #ffffff;
                    border: 1px solid #555;
                }
                QTabWidget::pane {
                    border: 1px solid #555;
                    background-color: #2b2b2b;
                }
                QTabBar::tab {
                    background-color: #3c3c3c;
                    color: white;
                    padding: 8px;
                    margin-right: 2px;
                }
                QTabBar::tab:selected {
                    background-color: #4a4a4a;
                }
                QGroupBox {
                    border: 2px solid #555;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                    color: #ffffff;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }
            """)
        elif theme == "light":
            # Estilo claro padrão do sistema
            pass
    
    def _create_ui(self):
        """Cria todos os elementos da interface"""
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # ========== BARRA SUPERIOR ==========
        top_bar = QHBoxLayout()
        
        # Título
        title_label = QLabel("🔬 SISTEMA DE INSPEÇÃO HÍBRIDO")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        top_bar.addWidget(title_label)
        
        top_bar.addStretch()
        
        # Botão de status
        self.status_label = QLabel("🟢 Conectado")
        top_bar.addWidget(self.status_label)
        
        main_layout.addLayout(top_bar)
        
        # ========== ABA PRINCIPAL ==========
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Aba: Captura
        self._create_capture_tab()
        
        # Aba: Inspeção
        self._create_inspection_tab()
        
        # Aba: Resultados
        self._create_results_tab()
        
        # Aba: Configurações
        self._create_settings_tab()
        
        # ========== BARRA INFERIOR ==========
        bottom_bar = QHBoxLayout()
        
        # Botão iniciar servidor web
        self.web_server_btn = QPushButton("🌐 Iniciar Servidor Web")
        self.web_server_btn.clicked.connect(self.toggle_web_server)
        bottom_bar.addWidget(self.web_server_btn)
        
        bottom_bar.addStretch()
        
        # Log de eventos
        self.log_btn = QPushButton("📋 Mostrar Log")
        self.log_btn.clicked.connect(self.show_log_window)
        bottom_bar.addWidget(self.log_btn)
        
        # Botão sair
        exit_btn = QPushButton("❌ Sair")
        exit_btn.clicked.connect(self.close)
        bottom_bar.addWidget(exit_btn)
        
        main_layout.addLayout(bottom_bar)
    
    def _create_capture_tab(self):
        """Cria aba de captura de imagem"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Grupo: Controles de captura
        capture_group = QGroupBox("Controle de Câmera")
        capture_layout = QVBoxLayout()
        
        # Informações da câmera
        self.camera_info_label = QLabel("Câmera: Não inicializada")
        capture_layout.addWidget(self.camera_info_label)
        
        # Botões de captura
        btn_layout = QHBoxLayout()
        
        self.capture_btn = QPushButton("📸 Capturar Imagem")
        self.capture_btn.clicked.connect(self.capture_image)
        btn_layout.addWidget(self.capture_btn)
        
        self.capture_continuous_btn = QPushButton("🎥 Captura Contínua")
        self.capture_continuous_btn.setCheckable(True)
        self.capture_continuous_btn.clicked.connect(self.toggle_continuous_capture)
        btn_layout.addWidget(self.capture_continuous_btn)
        
        capture_layout.addLayout(btn_layout)
        
        # Timer para captura contínua
        self.capture_timer = QTimer()
        self.capture_timer.timeout.connect(self.capture_image)
        
        capture_group.setLayout(capture_layout)
        layout.addWidget(capture_group)
        
        # Grupo: Visualização da imagem
        image_group = QGroupBox("Visualização")
        image_layout = QVBoxLayout()
        
        self.image_label = QLabel("Imagem aparecerá aqui")
        self.image_label.setMinimumSize(640, 480)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 2px solid #555; background-color: #1a1a1a;")
        
        image_layout.addWidget(self.image_label)
        
        # Informações da imagem
        self.image_info_label = QLabel("Sem imagem")
        image_layout.addWidget(self.image_info_label)
        
        image_group.setLayout(image_layout)
        layout.addWidget(image_group)
        
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "📸 Captura")
        
        # Atualiza informações da câmera
        self.update_camera_info()
    
    def _create_inspection_tab(self):
        """Cria aba de inspeção"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Grupo: Tipo de inspeção
        inspection_group = QGroupBox("Tipo de Inspeção")
        inspection_layout = QVBoxLayout()
        
        # Seleção de tipo
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Tipo:"))
        
        self.inspection_type_combo = QComboBox()
        self.inspection_type_combo.addItems(["Segmentação", "Classificação"])
        type_layout.addWidget(self.inspection_type_combo)
        
        type_layout.addStretch()
        inspection_layout.addLayout(type_layout)
        
        # Botão executar
        self.inspect_btn = QPushButton("🔍 Executar Inspeção")
        self.inspect_btn.clicked.connect(self.perform_inspection)
        self.inspect_btn.setEnabled(True)  # Sempre habilitado (tem seu próprio fluxo de captura)
        
        inspection_layout.addWidget(self.inspect_btn)
        
        inspection_group.setLayout(inspection_layout)
        layout.addWidget(inspection_group)
        
        # Grupo: Resultados
        results_group = QGroupBox("Resultados")
        results_layout = QVBoxLayout()
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(200)
        results_layout.addWidget(self.results_text)
        
        # Tabela de defeitos (para segmentação)
        self.defects_table = QTableWidget()
        self.defects_table.setColumnCount(4)
        self.defects_table.setHorizontalHeaderLabels(["Classe", "Confiança", "X", "Y", "Largura", "Altura"])
        self.defects_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.defects_table.setMaximumHeight(150)
        results_layout.addWidget(self.defects_table)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        # Grupo: Ações
        actions_group = QGroupBox("Ações")
        actions_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 Salvar Resultados")
        self.save_btn.clicked.connect(self.save_results)
        self.save_btn.setEnabled(False)
        actions_layout.addWidget(self.save_btn)
        
        self.clear_btn = QPushButton("🗑️ Limpar")
        self.clear_btn.clicked.connect(self.clear_results)
        actions_layout.addWidget(self.clear_btn)
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "🔍 Inspeção")
    
    def _create_results_tab(self):
        """Cria aba de histórico de resultados"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Tabela de histórico
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(["Data/Hora", "Tipo", "Resultado", "Defeitos", "Ações"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(self.history_table)
        
        # Botões
        btn_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Atualizar")
        refresh_btn.clicked.connect(self.load_history)
        btn_layout.addWidget(refresh_btn)
        
        export_btn = QPushButton("📤 Exportar CSV")
        export_btn.clicked.connect(self.export_history)
        btn_layout.addWidget(export_btn)
        
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "📊 Histórico")
        
        # Carrega histórico inicial
        QTimer.singleShot(100, self.load_history)
    
    def _create_settings_tab(self):
        """Cria aba de configurações"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Grupo: Câmera
        camera_group = QGroupBox("Configurações da Câmera")
        camera_layout = QVBoxLayout()
        
        # Seleção de câmera
        cam_layout = QHBoxLayout()
        cam_layout.addWidget(QLabel("Câmera:"))
        
        self.camera_combo = QComboBox()
        self.camera_combo.addItems(["Basler (Automático)", "Webcam 0", "Webcam 1", "Mock"])
        cam_layout.addWidget(self.camera_combo)
        
        camera_layout.addLayout(cam_layout)
        
        # Botão recarregar câmera
        reload_btn = QPushButton("🔄 Recarregar Câmera")
        reload_btn.clicked.connect(self.reload_camera)
        camera_layout.addWidget(reload_btn)
        
        camera_group.setLayout(camera_layout)
        layout.addWidget(camera_group)
        
        # Grupo: Modelos
        model_group = QGroupBox("Configurações dos Modelos")
        model_layout = QVBoxLayout()
        
        # Threshold de confiança
        thresh_layout = QHBoxLayout()
        thresh_layout.addWidget(QLabel("Threshold:"))
        
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.0, 1.0)
        self.confidence_spin.setSingleStep(0.05)
        self.confidence_spin.setValue(0.7)
        thresh_layout.addWidget(self.confidence_spin)
        
        model_layout.addLayout(thresh_layout)
        
        # Botão recarregar modelos
        model_btn = QPushButton("🤖 Recarregar Modelos")
        model_btn.clicked.connect(self.reload_models)
        model_layout.addWidget(model_btn)
        
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        # Grupo: Sistema
        system_group = QGroupBox("Configurações do Sistema")
        system_layout = QVBoxLayout()
        
        # Auto-salvar
        self.auto_save_check = QCheckBox("Salvar resultados automaticamente")
        self.auto_save_check.setChecked(True)
        system_layout.addWidget(self.auto_save_check)
        
        # Auto-iniciar web
        self.auto_web_check = QCheckBox("Iniciar servidor web automaticamente")
        self.auto_web_check.setChecked(False)
        system_layout.addWidget(self.auto_web_check)
        
        system_group.setLayout(system_layout)
        layout.addWidget(system_group)

        # Grupo: Crop (pré-processamento)
        crop_group = QGroupBox("Crop / Pré-processamento")
        crop_layout = QVBoxLayout()

        crop_controls = QHBoxLayout()
        self.crop_check = QCheckBox("Habilitar Crop automático")
        self.crop_check.setChecked(False)
        self.crop_check.stateChanged.connect(self._on_crop_toggled)
        crop_controls.addWidget(self.crop_check)

        self.edit_crop_btn = QPushButton("Editar Crop")
        self.edit_crop_btn.clicked.connect(self._open_crop_editor)
        crop_controls.addWidget(self.edit_crop_btn)

        # Botão para resetar crop
        self.reset_crop_btn = QPushButton("Resetar Crop")
        self.reset_crop_btn.clicked.connect(self._reset_crop)
        crop_controls.addWidget(self.reset_crop_btn)

        # Botão para resetar e capturar imagem imediatamente
        self.reset_and_capture_btn = QPushButton("Reset + Capturar")
        self.reset_and_capture_btn.clicked.connect(self._reset_crop_and_capture)
        crop_controls.addWidget(self.reset_and_capture_btn)

        crop_layout.addLayout(crop_controls)
        self.crop_info_label = QLabel("Crop: nenhum")
        crop_layout.addWidget(self.crop_info_label)

        crop_group.setLayout(crop_layout)
        layout.addWidget(crop_group)

        # Grupo: Captura periódica
        periodic_group = QGroupBox("Captura Periódica (dataset)")
        periodic_layout = QHBoxLayout()

        periodic_left = QVBoxLayout()
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Intervalo (s):"))
        self.periodic_interval = QSpinBox()
        self.periodic_interval.setRange(1, 3600)
        self.periodic_interval.setValue(10)
        interval_layout.addWidget(self.periodic_interval)
        periodic_left.addLayout(interval_layout)

        save_layout = QHBoxLayout()
        save_layout.addWidget(QLabel("Pasta de salvamento:"))
        self.periodic_save_dir = QLineEdit(str(Path.cwd() / "data" / "periodic"))
        save_layout.addWidget(self.periodic_save_dir)
        browse_btn = QPushButton("...")
        browse_btn.clicked.connect(self._browse_save_dir)
        save_layout.addWidget(browse_btn)
        periodic_left.addLayout(save_layout)

        periodic_layout.addLayout(periodic_left)

        periodic_right = QVBoxLayout()
        self.periodic_btn = QPushButton("▶ Iniciar Captura Periódica")
        self.periodic_btn.setCheckable(True)
        self.periodic_btn.clicked.connect(self._toggle_periodic_capture)
        periodic_right.addWidget(self.periodic_btn)
        periodic_right.addStretch()

        periodic_layout.addLayout(periodic_right)
        periodic_group.setLayout(periodic_layout)
        layout.addWidget(periodic_group)
        
        layout.addStretch()
        
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "⚙️ Configurações")
    
    def _create_system_tray(self):
        """Cria ícone na bandeja do sistema"""
        self.tray_icon = QSystemTrayIcon(self)
        
        # Usa ícone padrão do sistema ou personalizado
        app_icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
        self.tray_icon.setIcon(app_icon)
        
        # Menu do tray
        tray_menu = QMenu()
        
        show_action = QAction("Mostrar", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        hide_action = QAction("Ocultar", self)
        hide_action.triggered.connect(self.hide)
        tray_menu.addAction(hide_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("Sair", self)
        quit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        # Conecta clique no ícone
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
    
    def _connect_core_callbacks(self):
        """Conecta callbacks do core à interface"""
        
        def on_capture_completed(data):
            # schedule UI update on main thread
            QTimer.singleShot(0, lambda: self.log_message(f"📸 Captura completada: {data.get('camera_info', {}).get('type', 'N/A')}"))
        
        def on_inspection_completed(data, inspection_type):
            self.log_message(f"✅ {inspection_type.capitalize()} completada")
            self.display_inspection_results(data, inspection_type)
        
        # Registra callbacks
        self.core.register_callback("capture_completed", on_capture_completed)
        # Recebe notificações quando captura periódica salva um arquivo
        def on_periodic_saved(data):
            path = data.get("path")
            ts = datetime.fromtimestamp(data.get("timestamp", time.time())).isoformat()
            # schedule on UI thread
            QTimer.singleShot(0, lambda: self.log_message(f"💾 Captura periódica salva: {path} @ {ts}"))

        self.core.register_callback("periodic_capture_saved", on_periodic_saved)
        
        # Para outros eventos, podemos adicionar mais callbacks
    
    # ========== MÉTODOS DE CONTROLE ==========
    
    def update_camera_info(self):
        """Atualiza informações da câmera na UI"""
        try:
            info = self.core.get_system_info()
            camera_info = info.get("camera", {})
            
            camera_type = camera_info.get("type", "Desconhecida")
            status = "✅" if camera_info.get("initialized", False) else "❌"
            
            self.camera_info_label.setText(
                f"Câmera: {camera_type} {status}\n"
                f"Resolução: {camera_info.get('width', '?')}x{camera_info.get('height', '?')}"
            )
            
        except Exception as e:
            self.camera_info_label.setText(f"Câmera: Erro - {e}")

    def _on_crop_toggled(self, state: int):
        """Habilita/desabilita crop automático"""
        self.crop_enabled = bool(state)
        self.crop_info_label.setText(f"Crop: {'ativo' if self.crop_enabled else 'inativo'}")
        self.log_message(f"⚙️ Crop automático {'ativado' if self.crop_enabled else 'desativado'}")

    def _reset_crop(self):
        """Reseta configuração de crop (desabilita e limpa bbox)"""
        self.crop_bbox = None
        self.crop_check.setChecked(False)
        self.crop_enabled = False
        self.crop_info_label.setText("Crop: nenhum")
        self.log_message("✂️ Crop resetado")

    def _reset_crop_and_capture(self):
        """Reseta o crop e inicia captura imediata"""
        # Reseta primeiro
        self._reset_crop()
        # Dispara captura (usa o mesmo fluxo que o botão de captura)
        QTimer.singleShot(50, self.capture_image)

    def _open_crop_editor(self):
        """Abre diálogo para selecionar região de crop usando a imagem atual"""
        # Preferir imagem RAW (não processada) para seleção do crop
        img_for_edit = self.raw_image if self.raw_image is not None else self.current_image
        if img_for_edit is None:
            QMessageBox.warning(self, "Sem Imagem", "Capture uma imagem para editar o crop")
            return

        dlg = CropDialog(img_for_edit, parent=self)
        if dlg.exec_() == QDialog.Accepted and dlg.bbox:
            self.crop_bbox = dlg.bbox
            self.crop_info_label.setText(f"Crop: {self.crop_bbox}")
            self.log_message(f"✂️ Crop definido: {self.crop_bbox}")

    def _browse_save_dir(self):
        dirpath = QFileDialog.getExistingDirectory(self, "Escolher pasta", str(Path.cwd()))
        if dirpath:
            self.periodic_save_dir.setText(dirpath)

    def _toggle_periodic_capture(self, checked: bool):
        if checked:
            interval = float(self.periodic_interval.value())
            save_dir = self.periodic_save_dir.text()
            try:
                # Se crop automático estiver ativo e bbox definido, passa ops de preprocessamento
                ops = None
                if self.crop_enabled and self.crop_bbox:
                    ops = [{"name": "crop", "bbox": self.crop_bbox}]
                self.core.start_periodic_capture(interval, save_dir, preprocess_ops=ops)
                self.periodic_btn.setText("⏸️ Parar Captura Periódica")
                self.log_message(f"▶ Captura periódica iniciada (intervalo {interval}s) -> {save_dir}")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Não foi possível iniciar captura periódica:\n{e}")
                self.periodic_btn.setChecked(False)
        else:
            try:
                self.core.stop_periodic_capture()
                self.periodic_btn.setText("▶ Iniciar Captura Periódica")
                self.log_message("⏸️ Captura periódica parada")
            except Exception as e:
                QMessageBox.warning(self, "Erro", f"Erro ao parar captura periódica:\n{e}")
    
    def capture_image(self):
        """Captura uma imagem (em thread separada)"""
        self.capture_btn.setEnabled(False)
        self.status_label.setText("🟡 Capturando...")
        
        # Cria e inicia thread de captura
        self.capture_thread = CaptureThread(self.core)
        self.capture_thread.image_captured.connect(self.on_image_captured)
        self.capture_thread.error_occurred.connect(self.on_capture_error)
        self.capture_thread.start()
    
    @pyqtSlot(dict)
    def on_image_captured(self, result: dict):
        """Slot chamado quando imagem é capturada"""
        self.capture_btn.setEnabled(True)
        self.status_label.setText("🟢 Pronto")
        # Guarda imagem raw e aplica pré-processamento somente para exibição/inspeção
        raw = result.get("image")
        self.raw_image = raw

        image = raw
        if self.crop_enabled and self.crop_bbox:
            try:
                ops = [{"name": "crop", "bbox": self.crop_bbox}]
                image = self.core.preprocess_image(raw, ops)
            except Exception as e:
                self.log_message(f"❌ Falha ao aplicar crop: {e}")

        self.current_image = image
        
        # Atualiza UI
        self.display_image(self.current_image)
        
        # Mostra informações
        shape = self.current_image.shape if self.current_image is not None else "N/A"
        self.image_info_label.setText(
            f"Resolução: {shape} | "
            f"Câmera: {result.get('camera_info', {}).get('type', 'N/A')} | "
            f"Hora: {result.get('timestamp', 'N/A')}"
        )
        
        self.log_message(f"✅ Imagem capturada: {shape}")
        # Se solicitamos inspeção após a captura, inicia agora
        if getattr(self, '_inspect_after_capture', None):
            try:
                inspection_type = self._inspect_after_capture
                ui_text = "Segmentação" if inspection_type == "segmentation" else "Classificação"
                # limpa flag antes de iniciar para evitar loops
                self._inspect_after_capture = None
                QTimer.singleShot(50, lambda: self._start_inspection(inspection_type, ui_text))
            except Exception as e:
                self.log_message(f"❌ Falha ao iniciar inspeção após captura: {e}")

    @pyqtSlot(str)
    def on_capture_error(self, error_msg: str):
        """Slot chamado quando há erro na captura"""
        self.capture_btn.setEnabled(True)
        self.status_label.setText("🔴 Erro")
        
        QMessageBox.warning(self, "Erro na Captura", f"Falha ao capturar imagem:\n{error_msg}")
        self.log_message(f"❌ Erro na captura: {error_msg}")
    
    def display_image(self, image: np.ndarray):
        """Exibe imagem na label"""
        if image is None:
            return
        
        # Converte BGR (OpenCV) para RGB
        if len(image.shape) == 3 and image.shape[2] == 3:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = image
        
        # Cria QImage
        h, w, ch = image_rgb.shape
        bytes_per_line = ch * w
        qimage = QImage(image_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # Cria QPixmap e exibe
        pixmap = QPixmap.fromImage(qimage)
        
        # Escala mantendo proporção
        label_size = self.image_label.size()
        scaled_pixmap = pixmap.scaled(label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        self.image_label.setPixmap(scaled_pixmap)
    
    def toggle_continuous_capture(self, checked: bool):
        """Ativa/desativa captura contínua"""
        if checked:
            self.capture_continuous_btn.setText("⏸️ Parar Captura")
            self.capture_timer.start(1000)  # 1 segundo
            self.log_message("🎥 Captura contínua iniciada")
        else:
            self.capture_continuous_btn.setText("🎥 Captura Contínua")
            self.capture_timer.stop()
            self.log_message("⏸️ Captura contínua parada")
    
    def perform_inspection(self):
        """Executa inspeção na imagem dedicada da aba de Inspeção."""
        # Mapeia texto da UI (pt-BR) para tipos do core (en)
        ui_text = self.inspection_type_combo.currentText()
        idx = self.inspection_type_combo.currentIndex()
        map_types = {0: "segmentation", 1: "classification"}
        inspection_type = map_types.get(idx, "classification")

        # Se não há imagem de inspeção, capture primeiro
        if self.inspection_image is None:
            self._inspect_after_capture = inspection_type
            self.log_message("📸 Aguardando captura para inspeção...")
            # Cria thread de captura SEPARADA para inspeção
            self.inspection_capture_thread = CaptureThread(self.core)
            self.inspection_capture_thread.image_captured.connect(self._on_inspection_capture_completed)
            self.inspection_capture_thread.error_occurred.connect(self._on_inspection_capture_error)
            self.inspection_capture_thread.start()
            return

        # Caso já tenhamos imagem de inspeção, inicia a inspeção imediatamente
        self._start_inspection(inspection_type, ui_text)

    def _start_inspection(self, inspection_type: str, ui_text: str):
        """Inicia a thread de inspeção assumindo que `self.inspection_image` existe."""
        # Desabilita botão durante inspeção
        self.inspect_btn.setEnabled(False)
        # Mostra texto da UI enquanto executa
        self.status_label.setText(f"🟡 {ui_text}...")

        # Cria e inicia thread de inspeção com tipo do core
        # Usa inspection_image (fluxo independente da aba de captura)
        self.inspection_thread = InspectionThread(self.core, inspection_type, self.inspection_image)
        self.inspection_thread.inspection_completed.connect(self.on_inspection_completed)
        self.inspection_thread.error_occurred.connect(self.on_inspection_error)
        self.inspection_thread.start()
    
    def _on_inspection_capture_completed(self, result: dict):
        """Slot para captura dedicada à inspeção (fluxo independente)."""
        # Guarda imagem apenas para inspeção (não afeta aba de captura)
        raw = result.get("image")
        self.inspection_raw_image = raw

        image = raw
        if self.crop_enabled and self.crop_bbox:
            try:
                ops = [{"name": "crop", "bbox": self.crop_bbox}]
                image = self.core.preprocess_image(raw, ops)
            except Exception as e:
                self.log_message(f"❌ Falha ao aplicar crop: {e}")

        self.inspection_image = image

        # Se solicitamos inspeção após a captura, inicia agora
        if getattr(self, '_inspect_after_capture', None):
            try:
                inspection_type = self._inspect_after_capture
                ui_text = "Segmentação" if inspection_type == "segmentation" else "Classificação"
                # limpa flag antes de iniciar para evitar loops
                self._inspect_after_capture = None
                QTimer.singleShot(50, lambda: self._start_inspection(inspection_type, ui_text))
            except Exception as e:
                self.log_message(f"❌ Falha ao iniciar inspeção após captura: {e}")

    def _on_inspection_capture_error(self, error_msg: str):
        """Erro na captura para inspeção."""
        QMessageBox.warning(self, "Erro na Captura para Inspeção", f"Falha ao capturar imagem:\n{error_msg}")
        self.log_message(f"❌ Erro na captura para inspeção: {error_msg}")
    
    @pyqtSlot(dict, str)
    def on_inspection_completed(self, result: dict, inspection_type: str):
        """Slot chamado quando inspeção é completada"""
        self.inspect_btn.setEnabled(True)
        self.status_label.setText("🟢 Pronto")
        self.save_btn.setEnabled(True)
        
        self.current_results = result
        
        self.log_message(f"✅ {inspection_type.capitalize()} completada")
        
        # Se auto-salvar está ativado
        if self.auto_save_check.isChecked():
            self.save_results()
    
    @pyqtSlot(str)
    def on_inspection_error(self, error_msg: str):
        """Slot chamado quando há erro na inspeção"""
        self.inspect_btn.setEnabled(True)
        self.status_label.setText("🔴 Erro")
        
        QMessageBox.warning(self, "Erro na Inspeção", f"Falha na inspeção:\n{error_msg}")
        self.log_message(f"❌ Erro na inspeção: {error_msg}")
    
    def display_inspection_results(self, result: dict, inspection_type: str):
        """Exibe resultados da inspeção"""
        # Limpa resultados anteriores
        self.results_text.clear()
        self.defects_table.setRowCount(0)
        
        if inspection_type == "classification":
            defects_info = result.get("defects_info", [])
            if defects_info:
                defect = defects_info[0]
                status = result.get("status", "unknown")
                
                if status == "indeterminado":
                    text = "🔶 INDETERMINADO\n\n"
                    text += "Confiança abaixo do limite.\n"
                    text += "Recomenda-se nova captura."
                    text_color = "orange"
                else:
                    class_name = defect.get("class", "Desconhecido")
                    confidence = defect.get("confidence", 0)
                    is_bad = result.get("defects_detected", False)
                    
                    if is_bad:
                        text = f"❌ FRUTA RUIM\n\n"
                        text += f"Classe: {class_name}\n"
                        text += f"Confiança: {confidence:.1%}"
                        text_color = "red"
                    else:
                        text = f"✅ FRUTA BOA\n\n"
                        text += f"Classe: {class_name}\n"
                        text += f"Confiança: {confidence:.1%}"
                        text_color = "green"
                
                self.results_text.setText(text)
                self.results_text.setStyleSheet(f"color: {text_color}; font-weight: bold;")
        
        elif inspection_type == "segmentation":
            defects = result.get("defects", [])
            has_defects = result.get("has_defects", False)
            total = result.get("total_defects", 0)
            
            if has_defects:
                text = f"⚠️  {total} DEFEITO(S) ENCONTRADO(S)\n\n"
                text_color = "orange"
            else:
                text = f"✅ NENHUM DEFEITO ENCONTRADO\n\n"
                text_color = "green"
            
            self.results_text.setText(text)
            self.results_text.setStyleSheet(f"color: {text_color}; font-weight: bold;")
            
            # Preenche tabela de defeitos
            if defects:
                self.defects_table.setRowCount(len(defects))
                for i, defect in enumerate(defects):
                    self.defects_table.setItem(i, 0, QTableWidgetItem(defect.get("class_name", "N/A")))
                    self.defects_table.setItem(i, 1, QTableWidgetItem(f"{defect.get('confidence', 0):.3f}"))
                    
                    bbox = defect.get("bbox", [0, 0, 0, 0])
                    if len(bbox) == 4:
                        x, y, w, h = bbox
                        self.defects_table.setItem(i, 2, QTableWidgetItem(f"{x:.0f}"))
                        self.defects_table.setItem(i, 3, QTableWidgetItem(f"{y:.0f}"))
                        self.defects_table.setItem(i, 4, QTableWidgetItem(f"{w:.0f}"))
                        self.defects_table.setItem(i, 5, QTableWidgetItem(f"{h:.0f}"))
    
    def save_results(self):
        """Salva resultados atuais"""
        if self.current_results is None or self.inspection_image is None:
            QMessageBox.warning(self, "Sem Dados", "Não há resultados para salvar!")
            return
        
        try:
            # Prepara dados da inspeção (usa inspection_image, não current_image)
            inspection_type = self.inspection_type_combo.currentText().lower()
            inspection_data = {
                "inspection_type": inspection_type,
                "timestamp": datetime.now().isoformat(),
                "image": self.inspection_image,
                "results": self.current_results
            }
            
            # Salva via core
            saved_path = self.core.save_inspection(inspection_data)
            
            if saved_path:
                QMessageBox.information(self, "Salvo", f"Resultados salvos em:\n{saved_path}")
                self.log_message(f"💾 Resultados salvos: {saved_path}")
                self.load_history()  # Atualiza histórico
            else:
                QMessageBox.warning(self, "Erro", "Não foi possível salvar resultados")
                
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao salvar:\n{str(e)}")
            self.log_message(f"❌ Erro ao salvar: {e}")
    
    def clear_results(self):
        """Limpa resultados atuais"""
        self.current_image = None
        self.current_results = None
        
        self.image_label.clear()
        self.image_label.setText("Imagem aparecerá aqui")
        self.image_info_label.setText("Sem imagem")
        
        self.results_text.clear()
        self.defects_table.setRowCount(0)
        
        self.inspect_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        
        self.log_message("🧹 Resultados limpos")
    
    def _clear_inspection_results(self):
        """Limpa resultados da aba de Inspeção (independente)"""
        self.inspection_image = None
        self.inspection_raw_image = None
        self.current_results = None
        
        self.results_text.clear()
        self.defects_table.setRowCount(0)
        
        self.inspect_btn.setEnabled(True)
        self.save_btn.setEnabled(False)
        
        self.log_message("🧹 Resultados de inspeção limpos")
    
    def load_history(self):
        """Carrega histórico de inspeções"""
        # TODO: Implementar carregamento real do diretório de resultados
        # Por enquanto, apenas uma demo
        
        self.history_table.setRowCount(3)  # Demo
        
        # Linha 1
        self.history_table.setItem(0, 0, QTableWidgetItem("2024-01-01 10:30:00"))
        self.history_table.setItem(0, 1, QTableWidgetItem("Classificação"))
        self.history_table.setItem(0, 2, QTableWidgetItem("✅ BOA"))
        self.history_table.setItem(0, 3, QTableWidgetItem("0"))
        
        # Botão de ação
        view_btn = QPushButton("👁️ Ver")
        view_btn.clicked.connect(lambda: self.view_history_item(0))
        self.history_table.setCellWidget(0, 4, view_btn)
        
        # Linha 2
        self.history_table.setItem(1, 0, QTableWidgetItem("2024-01-01 10:31:00"))
        self.history_table.setItem(1, 1, QTableWidgetItem("Segmentação"))
        self.history_table.setItem(1, 2, QTableWidgetItem("⚠️  2 defeitos"))
        self.history_table.setItem(1, 3, QTableWidgetItem("2"))
        
        view_btn2 = QPushButton("👁️ Ver")
        view_btn2.clicked.connect(lambda: self.view_history_item(1))
        self.history_table.setCellWidget(1, 4, view_btn2)
        
        # Linha 3
        self.history_table.setItem(2, 0, QTableWidgetItem("2024-01-01 10:32:00"))
        self.history_table.setItem(2, 1, QTableWidgetItem("Classificação"))
        self.history_table.setItem(2, 2, QTableWidgetItem("❌ RUIM"))
        self.history_table.setItem(2, 3, QTableWidgetItem("1"))
        
        view_btn3 = QPushButton("👁️ Ver")
        view_btn3.clicked.connect(lambda: self.view_history_item(2))
        self.history_table.setCellWidget(2, 4, view_btn3)
    
    def view_history_item(self, row: int):
        """Visualiza item do histórico"""
        QMessageBox.information(
            self, 
            "Visualizar", 
            f"Visualizando item {row + 1}\n\n"
            f"Em uma implementação real, esta função abriria\n"
            f"os resultados salvos no disco."
        )
    
    def export_history(self):
        """Exporta histórico como CSV"""
        # TODO: Implementar exportação real
        QMessageBox.information(
            self,
            "Exportar CSV",
            "Funcionalidade de exportação será implementada.\n"
            "O histórico será salvo em formato CSV."
        )
    
    def reload_camera(self):
        """Recarrega configuração da câmera"""
        try:
            # TODO: Implementar recarregamento real
            self.update_camera_info()
            QMessageBox.information(self, "Recarregar", "Configuração da câmera recarregada")
            self.log_message("🔄 Câmera recarregada")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao recarregar câmera:\n{str(e)}")
    
    def reload_models(self):
        """Recarrega modelos ML"""
        try:
            # TODO: Implementar recarregamento real
            new_threshold = self.confidence_spin.value()
            QMessageBox.information(
                self, 
                "Recarregar Modelos", 
                f"Modelos recarregados\nNovo threshold: {new_threshold}"
            )
            self.log_message(f"🔄 Modelos recarregados (threshold: {new_threshold})")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao recarregar modelos:\n{str(e)}")
    
    def toggle_web_server(self):
        """Inicia/para servidor web"""
        # TODO: Implementar controle do servidor web
        QMessageBox.information(
            self,
            "Servidor Web",
            "Funcionalidade será implementada.\n"
            "O servidor web permitirá acesso via navegador."
        )
    
    def show_log_window(self):
        """Mostra janela de logs"""
        # TODO: Implementar janela de logs completa
        log_text = "📋 LOG DO SISTEMA\n\n"
        log_text += "10:30:00 - Sistema iniciado\n"
        log_text += "10:30:05 - Câmera Basler conectada\n"
        log_text += "10:30:10 - Modelos carregados\n"
        log_text += "10:30:15 - Imagem capturada\n"
        log_text += "10:30:20 - Classificação executada\n"
        
        QMessageBox.information(self, "Log do Sistema", log_text)
    
    def log_message(self, message: str):
        """Adiciona mensagem ao log interno"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_text = self.results_text.toPlainText()
        log_text = f"[{timestamp}] {message}\n" + log_text
        self.results_text.setPlainText(log_text[:1000])  # Limita tamanho
    
    def on_tray_icon_activated(self, reason):
        """Lida com clique no ícone da bandeja"""
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.activateWindow()
    
    def closeEvent(self, event):
        """Lida com fechamento da janela"""
        reply = QMessageBox.question(
            self, 'Sair',
            'Deseja realmente sair?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Limpa recursos
            if hasattr(self, 'capture_timer'):
                self.capture_timer.stop()
            
            # Esconde para tray se configurado
            if DESKTOP_CONFIG["show_system_tray"]:
                event.ignore()
                self.hide()
                self.tray_icon.showMessage(
                    "Sistema de Inspeção",
                    "Aplicação minimizada para bandeja",
                    QSystemTrayIcon.Information,
                    2000
                )
            else:
                event.accept()
                self.core.cleanup()
                QApplication.quit()
        else:
            event.ignore()

# ============================================
# FUNÇÃO PRINCIPAL
# ============================================

def start_desktop_app(core: SystemCore = None):
    """
    Inicia a aplicação desktop.
    
    Args:
        core: Instância do SystemCore (se None, cria nova)
    """
    # Cria aplicação Qt
    app = QApplication(sys.argv)
    app.setApplicationName("Sistema de Inspeção")
    app.setApplicationDisplayName("Sistema de Inspeção Híbrido")
    
    # Cria core se não fornecido
    if core is None:
        core = SystemCore()
        if not core.initialize():
            QMessageBox.critical(
                None,
                "Erro de Inicialização",
                "Não foi possível inicializar o sistema."
            )
            return 1
    
    # Cria janela principal
    try:
        window = MainWindow(core)
        window.show()
        
        log.info("🖥️  Interface desktop inicializada")
        
        # Executa aplicação
        return app.exec_()
    except Exception as e:
        log.error(f"❌ Erro ao inicializar desktop: {e}")
        QMessageBox.critical(
            None,
            "Erro Crítico",
            f"Erro ao inicializar a interface:\n{str(e)}"
        )
        core.cleanup()
        return 1   