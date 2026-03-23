"""Builder for the Inspection tab UI component."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QComboBox, QDoubleSpinBox
)
from ..panels import InspectionResultsPanel


def build_inspection_tab(main_window):
    """
    Build and return the Inspection tab.
    
    Args:
        main_window: Reference to MainWindow instance for signal/slot connections
    
    Returns:
        QWidget: The configured Inspection tab
    """
    tab = QWidget()
    layout = QVBoxLayout()
    layout.setContentsMargins(5, 5, 5, 5)
    layout.setSpacing(5)

    # Inspection Type Group
    inspection_group = QGroupBox('Tipo de Inspeção')
    inspection_layout = QHBoxLayout()
    inspection_layout.setContentsMargins(5, 5, 5, 5)
    inspection_layout.setSpacing(5)

    inspection_layout.addWidget(QLabel('Tipo:'))
    main_window.inspection_type_combo = QComboBox()
    main_window.inspection_type_combo.addItems(['Segmentação', 'Detecção', 'Classificação'])
    main_window.inspection_type_combo.currentIndexChanged.connect(main_window._on_inspection_type_changed)
    inspection_layout.addWidget(main_window.inspection_type_combo)

    inspection_layout.addWidget(QLabel('Modelo:'))
    main_window.model_combo = QComboBox()
    main_window.model_combo.setMinimumWidth(150)
    main_window.model_combo.setMaximumWidth(250)
    inspection_layout.addWidget(main_window.model_combo)

    main_window._on_inspection_type_changed()

    inspection_layout.addWidget(QLabel('Threshold:'))
    main_window.confidence_spin = QDoubleSpinBox()
    main_window.confidence_spin.setRange(0.0, 1.0)
    main_window.confidence_spin.setSingleStep(0.05)
    main_window.confidence_spin.setValue(0.7)
    main_window.confidence_spin.setMaximumWidth(80)
    inspection_layout.addWidget(main_window.confidence_spin)

    model_reload_btn = QPushButton(' Recarregar')
    model_reload_btn.clicked.connect(main_window.reload_models)
    model_reload_btn.setMaximumWidth(110)
    inspection_layout.addWidget(model_reload_btn)

    main_window.inspect_btn = QPushButton(' Executar')
    main_window.inspect_btn.clicked.connect(main_window.perform_inspection)
    main_window.inspect_btn.setEnabled(True)
    main_window.inspect_btn.setMaximumWidth(120)
    main_window.inspect_btn.setToolTip(
        'Executa análise inteligente na imagem.\n'
        'Segmentação: Detecta defeitos (bbox)\n'
        'Detecção: Detecta objetos (bbox)\n'
        'Classificação: Classifica BOM ou RUIM'
    )
    inspection_layout.addWidget(main_window.inspect_btn)

    inspection_layout.addStretch()
    inspection_group.setLayout(inspection_layout)
    inspection_group.setMaximumHeight(70)
    layout.addWidget(inspection_group, 0)

    # Results Panel
    main_window.inspection_results_panel = InspectionResultsPanel()
    layout.addWidget(main_window.inspection_results_panel, 1)

    # Actions Group
    actions_group = QGroupBox('Ações')
    actions_layout = QHBoxLayout()
    actions_layout.setContentsMargins(8, 8, 8, 8)
    actions_layout.setSpacing(8)

    main_window.vp_btn = QPushButton('Verdadeiro Positivo')
    main_window.vp_btn.clicked.connect(lambda: main_window._save_categoria('verdadeiro_positivo'))
    main_window.vp_btn.setEnabled(False)
    main_window.vp_btn.setMaximumWidth(140)
    main_window.vp_btn.setMinimumHeight(32)
    main_window.vp_btn.setToolTip('Move a imagem para data/verdadeiro_positivo')
    actions_layout.addWidget(main_window.vp_btn)

    main_window.vn_btn = QPushButton('Verdadeiro Negativo')
    main_window.vn_btn.clicked.connect(lambda: main_window._save_categoria('verdadeiro_negativo'))
    main_window.vn_btn.setEnabled(False)
    main_window.vn_btn.setMaximumWidth(140)
    main_window.vn_btn.setMinimumHeight(32)
    main_window.vn_btn.setToolTip('Move a imagem para data/verdadeiro_negativo')
    actions_layout.addWidget(main_window.vn_btn)

    main_window.fp_btn = QPushButton('Falso Positivo')
    main_window.fp_btn.clicked.connect(lambda: main_window._save_categoria('falso_positivo'))
    main_window.fp_btn.setEnabled(False)
    main_window.fp_btn.setMaximumWidth(140)
    main_window.fp_btn.setMinimumHeight(32)
    main_window.fp_btn.setToolTip('Move a imagem para data/falso_positivo')
    actions_layout.addWidget(main_window.fp_btn)

    main_window.fn_btn = QPushButton('Falso Negativo')
    main_window.fn_btn.clicked.connect(lambda: main_window._save_categoria('falso_negativo'))
    main_window.fn_btn.setEnabled(False)
    main_window.fn_btn.setMaximumWidth(140)
    main_window.fn_btn.setMinimumHeight(32)
    main_window.fn_btn.setToolTip('Move a imagem para data/falso_negativo')
    actions_layout.addWidget(main_window.fn_btn)

    main_window.copy_results_btn = QPushButton(' Copiar Resultados')
    main_window.copy_results_btn.clicked.connect(main_window._copy_inspection_results)
    main_window.copy_results_btn.setEnabled(False)
    main_window.copy_results_btn.setMaximumWidth(160)
    main_window.copy_results_btn.setMinimumHeight(32)
    main_window.copy_results_btn.setToolTip('Copia os resultados para a área de transferência')
    actions_layout.addWidget(main_window.copy_results_btn)

    main_window.export_image_btn = QPushButton(' Exportar Imagem')
    main_window.export_image_btn.clicked.connect(main_window._export_inspection_image)
    main_window.export_image_btn.setEnabled(False)
    main_window.export_image_btn.setMaximumWidth(160)
    main_window.export_image_btn.setMinimumHeight(32)
    main_window.export_image_btn.setToolTip('Salva a imagem anotada em arquivo')
    actions_layout.addWidget(main_window.export_image_btn)

    main_window.clear_btn = QPushButton(' Limpar')
    main_window.clear_btn.clicked.connect(main_window._clear_inspection_results)
    main_window.clear_btn.setMaximumWidth(100)
    main_window.clear_btn.setMinimumHeight(32)
    main_window.clear_btn.setToolTip('Remove os resultados exibidos')
    actions_layout.addWidget(main_window.clear_btn)

    actions_layout.addStretch()
    actions_group.setLayout(actions_layout)
    actions_group.setMaximumHeight(90)
    layout.addWidget(actions_group, 0)

    tab.setLayout(layout)
    main_window.tab_widget.addTab(tab, ' Inspeção')

    return tab
