"""Builder for the Capture tab UI component."""

from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QSpinBox, QLineEdit
)
from PyQt5.QtCore import Qt, QTimer


def build_capture_tab(main_window):
    """
    Build and return the Capture tab.
    
    Args:
        main_window: Reference to MainWindow instance for signal/slot connections
    
    Returns:
        QWidget: The configured Capture tab
    """
    tab = QWidget()
    layout = QVBoxLayout()

    # Capture Control Group
    capture_group = QGroupBox('Controle de Câmera')
    capture_layout = QVBoxLayout()

    main_window.camera_info_label = QLabel('Câmera: Não inicializada')
    capture_layout.addWidget(main_window.camera_info_label)

    btn_layout = QHBoxLayout()

    main_window.capture_btn = QPushButton(' Capturar Imagem')
    main_window.capture_btn.clicked.connect(main_window.capture_image)
    main_window.capture_btn.setToolTip(
        "Captura uma única imagem da câmera.\n\nO que faz:\n"
        "• Conecta à câmera (com fallback automático)\n"
        "• Captura 1 frame em alta qualidade\n"
        "• Aplica crop automático (se habilitado)\n"
        "• Exibe imagem neste painel\n\nUso:\n"
        "1. Posicione o produto\n"
        "2. Clique para capturar\n"
        "3. Vá para aba 'Inspeção' para analisar\n\n"
        "Para preview contínuo:\n"
        "clique em 'Captura Contínua'"
    )
    btn_layout.addWidget(main_window.capture_btn)

    main_window.capture_continuous_btn = QPushButton(' Abrir Streaming')
    main_window.capture_continuous_btn.setCheckable(True)
    main_window.capture_continuous_btn.clicked.connect(main_window.toggle_continuous_capture)
    main_window.capture_continuous_btn.setToolTip(
        'Ativa streaming em tempo real (30 FPS).\n\nO que faz:\n'
        '• Thread separada captura a cada 30ms\n'
        '• Mostra preview contínuo da câmera\n'
        '• Exibe FPS em tempo real\n'
        '• Sem travamento da interface\n\nUso:\n'
        '• Clique para iniciar streaming\n'
        '• Clique novamente para parar\n'
        '• Veja o FPS no canto inferior\n\n'
        'Perfeito para posicionar o produto'
    )
    btn_layout.addWidget(main_window.capture_continuous_btn)

    capture_layout.addLayout(btn_layout)

    main_window.capture_timer = QTimer()
    main_window.capture_timer.timeout.connect(main_window.capture_image)

    capture_group.setLayout(capture_layout)
    layout.addWidget(capture_group)

    # Image Visualization Group
    image_group = QGroupBox('Visualização')
    image_layout = QVBoxLayout()

    main_window.image_label = QLabel('Imagem aparecerá aqui')
    main_window.image_label.setMinimumSize(640, 480)
    main_window.image_label.setAlignment(Qt.AlignCenter)
    main_window.image_label.setStyleSheet('border: 2px solid #555; background-color: #1a1a1a;')
    image_layout.addWidget(main_window.image_label)

    main_window.image_info_label = QLabel('Sem imagem')
    image_layout.addWidget(main_window.image_info_label)

    image_group.setLayout(image_layout)
    layout.addWidget(image_group)

    # Periodic Capture Group
    periodic_group = QGroupBox(' Captura Periódica (dataset)')
    periodic_layout = QHBoxLayout()

    periodic_left = QVBoxLayout()

    interval_layout = QHBoxLayout()
    interval_layout.addWidget(QLabel('Intervalo (s):'))
    main_window.periodic_interval = QSpinBox()
    main_window.periodic_interval.setRange(1, 3600)
    main_window.periodic_interval.setValue(10)
    interval_layout.addWidget(main_window.periodic_interval)
    periodic_left.addLayout(interval_layout)

    save_layout = QHBoxLayout()
    save_layout.addWidget(QLabel('Pasta de salvamento:'))
    main_window.periodic_save_dir = QLineEdit(str(Path.cwd() / 'data' / 'periodic'))
    save_layout.addWidget(main_window.periodic_save_dir)
    browse_btn = QPushButton('...')
    browse_btn.clicked.connect(main_window._browse_save_dir)
    save_layout.addWidget(browse_btn)
    periodic_left.addLayout(save_layout)

    periodic_layout.addLayout(periodic_left)

    periodic_right = QVBoxLayout()
    main_window.periodic_btn = QPushButton(' Iniciar Captura Periódica')
    main_window.periodic_btn.setCheckable(True)
    main_window.periodic_btn.clicked.connect(main_window._toggle_periodic_capture)
    periodic_right.addWidget(main_window.periodic_btn)
    periodic_right.addStretch()
    periodic_layout.addLayout(periodic_right)

    periodic_group.setLayout(periodic_layout)
    layout.addWidget(periodic_group)

    tab.setLayout(layout)
    main_window.tab_widget.addTab(tab, ' Captura')
    main_window.update_camera_info()

    return tab
