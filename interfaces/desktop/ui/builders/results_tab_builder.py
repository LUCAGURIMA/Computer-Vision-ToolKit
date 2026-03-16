"""Builder for the Results/History tab UI component."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QComboBox, QTableWidget, QHeaderView
)


def build_results_tab(main_window):
    """
    Build and return the Results/History tab.
    
    Args:
        main_window: Reference to MainWindow instance for signal/slot connections
    
    Returns:
        QWidget: The configured Results tab
    """
    tab = QWidget()
    layout = QVBoxLayout()

    # Filters Group
    filters_group = QGroupBox('Filtros')
    filters_layout = QHBoxLayout()

    filters_layout.addWidget(QLabel('Tipo:'))
    main_window.history_type_combo = QComboBox()
    main_window.history_type_combo.addItem('Carregando...')
    filters_layout.addWidget(main_window.history_type_combo)

    filters_layout.addWidget(QLabel('Modelo:'))
    main_window.history_model_combo = QComboBox()
    main_window.history_model_combo.setEditable(True)
    main_window.history_model_combo.addItem('Carregando...')
    filters_layout.addWidget(main_window.history_model_combo)

    filters_layout.addStretch()
    filters_group.setLayout(filters_layout)
    layout.addWidget(filters_group)

    # History Table
    main_window.history_table = QTableWidget()
    main_window.history_table.setColumnCount(6)
    main_window.history_table.setHorizontalHeaderLabels(
        ['Data/Hora', 'Tipo', 'Modelo', 'Resultado', 'Defeitos', 'Máscara']
    )
    main_window.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    main_window.history_table.setMinimumHeight(300)
    main_window.history_result_dirs = []
    layout.addWidget(main_window.history_table, 1)

    # Button Layout
    btn_layout = QHBoxLayout()

    refresh_btn = QPushButton(' Atualizar')
    refresh_btn.clicked.connect(main_window.load_history)
    btn_layout.addWidget(refresh_btn)

    export_btn = QPushButton(' Exportar CSV')
    export_btn.clicked.connect(main_window.export_history)
    btn_layout.addWidget(export_btn)

    btn_layout.addStretch()
    layout.addLayout(btn_layout)

    tab.setLayout(layout)
    main_window.tab_widget.addTab(tab, ' Histórico')

    return tab
