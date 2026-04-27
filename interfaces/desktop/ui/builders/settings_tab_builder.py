"""Builder for the Settings tab UI component."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QComboBox, QCheckBox, QTextEdit,
    QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt
from config import DESKTOP_CONFIG


def build_settings_tab(main_window):
    """
    Build and return the Settings tab.
    
    Args:
        main_window: Reference to MainWindow instance for signal/slot connections
    
    Returns:
        QWidget: The configured Settings tab
    """
    tab = QWidget()
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    scroll_widget = QWidget()
    scroll_widget.setStyleSheet('''
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QGroupBox {
            border: 2px solid #555;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
            color: #ffffff;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            color: #ffffff;
        }
        QGroupBox::indicator {
            width: 18px;
            height: 18px;
            background-color: #1a1a1a;
            border: 2px solid #888;
            border-radius: 3px;
        }
        QGroupBox::indicator:hover {
            border: 2px solid #aaa;
        }
        QGroupBox::indicator:checked {
            background-color: #0d47a1;
            border: 2px solid #0d47a1;
            image: url(data:image/svg+xml,%3Csvg%20xmlns=%22http://www.w3.org/2000/svg%22%20viewBox=%220%200%2024%2024%22%3E%3Cline%20x1=%224%22%20y1=%2212%22%20x2=%2210%22%20y2=%2218%22%20stroke=%22white%22%20stroke-width=%222%22/%3E%3Cline%20x1=%2210%22%20y1=%2218%22%20x2=%2220%22%20y2=%228%22%20stroke=%22white%22%20stroke-width=%222%22/%3E%3C/svg%3E);
        }
        QLabel {
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
        QComboBox {
            background-color: #3c3c3c;
            color: white;
            border: 1px solid #555;
            padding: 4px;
            border-radius: 2px;
            min-height: 24px;
            min-width: 100px;
        }
        QComboBox:hover {
            border: 1px solid #777;
            background-color: #4a4a4a;
        }
        QComboBox:focus {
            border: 2px solid #0d47a1;
            background-color: #454545;
        }
        QComboBox::drop-down {
            border: none;
            width: 30px;
            background-color: transparent;
        }
        QComboBox:on {
            background-color: #454545;
            border: 2px solid #0d47a1;
        }
        QComboBox QAbstractItemView {
            background-color: #3c3c3c;
            color: white;
            border: 1px solid #555;
            selection-background-color: #0d47a1;
            selection-color: white;
        }
        QComboBox QAbstractItemView::item:hover {
            background-color: #505050;
        }
        QComboBox QAbstractItemView::item:selected {
            background-color: #0d47a1;
        }
        QCheckBox {
            color: #ffffff;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            background-color: #3c3c3c;
            border: 1px solid #555;
            border-radius: 2px;
        }
        QCheckBox::indicator:checked {
            background-color: #4a4a4a;
        }
        QLineEdit {
            background-color: #3c3c3c;
            color: white;
            border: 1px solid #555;
            padding: 4px;
            border-radius: 2px;
        }
    ''')

    layout = QVBoxLayout(scroll_widget)

    # Camera Settings Group
    camera_group = QGroupBox('Configurações da Câmera')
    camera_layout = QVBoxLayout()

    main_window.camera_status_label = QLabel(' Câmera: Não inicializada')
    main_window.camera_status_label.setStyleSheet('font-weight: bold; font-size: 16px;')
    camera_layout.addWidget(main_window.camera_status_label)

    cam_select_layout = QHBoxLayout()
    cam_select_layout.addWidget(QLabel('Trocar câmera:'))
    main_window.camera_combo = QComboBox()
    main_window.camera_combo.setMinimumWidth(150)
    main_window.camera_combo.setMinimumHeight(28)
    main_window.camera_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    main_window.camera_combo.setMaxVisibleItems(10)
    main_window.camera_combo.setEditable(False)
    main_window.camera_combo.setFocusPolicy(3)
    main_window.camera_combo.currentIndexChanged.connect(main_window._on_camera_combo_changed)
    cam_select_layout.addWidget(main_window.camera_combo)
    camera_layout.addLayout(cam_select_layout)

    reload_btn = QPushButton(' Recarregar')
    reload_btn.setToolTip('Reconecta todas as câmeras e atualiza lista')
    reload_btn.clicked.connect(main_window._reload_cameras_completely)
    camera_layout.addWidget(reload_btn)

    camera_group.setLayout(camera_layout)
    layout.addWidget(camera_group)

    # System Settings Group
    system_group = QGroupBox('Configurações do Sistema')
    system_layout = QVBoxLayout()

    main_window.auto_save_check = QCheckBox('Salvar resultados automaticamente')
    main_window.auto_save_check.setChecked(True)
    system_layout.addWidget(main_window.auto_save_check)

    main_window.stream_popup_check = QCheckBox('Abrir streaming em janela popup')
    main_window.stream_popup_check.setChecked(DESKTOP_CONFIG.get('stream_in_popup', True))
    main_window.stream_popup_check.stateChanged.connect(main_window._on_stream_in_popup_toggled)
    system_layout.addWidget(main_window.stream_popup_check)

    system_group.setLayout(system_layout)
    layout.addWidget(system_group)

    # Crop/Preprocessing Group
    crop_group = QGroupBox('Crop / Pré-processamento')
    crop_layout = QVBoxLayout()

    crop_controls = QHBoxLayout()
    main_window.crop_check = QCheckBox('Habilitar Crop automático')
    main_window.crop_check.setChecked(False)
    main_window.crop_check.stateChanged.connect(main_window._on_crop_toggled)
    crop_controls.addWidget(main_window.crop_check)

    main_window.edit_crop_btn = QPushButton('Editar Crop')
    main_window.edit_crop_btn.clicked.connect(main_window._open_crop_editor)
    crop_controls.addWidget(main_window.edit_crop_btn)

    main_window.reset_crop_btn = QPushButton('Resetar Crop')
    main_window.reset_crop_btn.clicked.connect(main_window._reset_crop)
    crop_controls.addWidget(main_window.reset_crop_btn)

    main_window.reset_and_capture_btn = QPushButton('Reset + Capturar')
    main_window.reset_and_capture_btn.clicked.connect(main_window._reset_crop_and_capture)
    crop_controls.addWidget(main_window.reset_and_capture_btn)

    crop_layout.addLayout(crop_controls)

    main_window.crop_info_label = QLabel('Crop: nenhum')
    crop_layout.addWidget(main_window.crop_info_label)

    crop_group.setLayout(crop_layout)
    layout.addWidget(crop_group)

    # Logs Group
    logs_group = QGroupBox(' Logs do Sistema')
    logs_layout = QVBoxLayout()

    main_window.logs_text = QTextEdit()
    main_window.logs_text.setReadOnly(True)
    main_window.logs_text.setMaximumHeight(150)
    main_window.logs_text.setPlaceholderText('Logs do sistema aparecem aqui...')
    logs_layout.addWidget(main_window.logs_text)

    log_btn_layout = QHBoxLayout()
    clear_logs_btn = QPushButton(' Limpar Logs')
    clear_logs_btn.clicked.connect(main_window._clear_logs)
    log_btn_layout.addWidget(clear_logs_btn)

    export_logs_btn = QPushButton(' Exportar Logs')
    export_logs_btn.clicked.connect(main_window._export_logs)
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

    main_window.tab_widget.addTab(tab, ' Configurações')

    return tab
