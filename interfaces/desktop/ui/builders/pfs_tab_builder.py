"""Builder for the Basler PFS Profiles tab UI component."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QComboBox, QTableWidget, QHeaderView, QTextEdit
)
from PyQt5.QtGui import QFont


def build_pfs_tab(main_window):
    """
    Build and return the Basler PFS Profiles tab.
    
    Args:
        main_window: Reference to MainWindow instance for signal/slot connections
    
    Returns:
        QWidget: The configured PFS tab
    """
    tab = QWidget()
    layout = QVBoxLayout()

    # Title
    title = QLabel(' Gerenciamento de Perfis Basler (.pfs)')
    title.setFont(QFont('Arial', 18, QFont.Bold))
    layout.addWidget(title)

    # Controls Group
    controls_group = QGroupBox('Controles')
    controls_layout = QHBoxLayout()

    main_window.load_pfs_btn = QPushButton(' Carregar .pfs')
    main_window.load_pfs_btn.clicked.connect(main_window.load_pfs_file)
    controls_layout.addWidget(main_window.load_pfs_btn)

    main_window.save_pfs_btn = QPushButton(' Salvar .pfs')
    main_window.save_pfs_btn.clicked.connect(main_window.save_pfs_file)
    controls_layout.addWidget(main_window.save_pfs_btn)

    main_window.refresh_pfs_btn = QPushButton(' Atualizar')
    main_window.refresh_pfs_btn.clicked.connect(main_window.refresh_pfs_list)
    controls_layout.addWidget(main_window.refresh_pfs_btn)

    controls_layout.addStretch()
    controls_group.setLayout(controls_layout)
    layout.addWidget(controls_group)

    # Profiles Group
    profiles_group = QGroupBox('Perfis .pfs Disponíveis')
    profiles_layout = QVBoxLayout()

    profile_layout = QHBoxLayout()
    profile_layout.addWidget(QLabel('Perfil:'))
    main_window.pfs_profile_combo = QComboBox()
    main_window.pfs_profile_combo.currentTextChanged.connect(main_window.on_pfs_profile_selected)
    profile_layout.addWidget(main_window.pfs_profile_combo)

    main_window.delete_pfs_btn = QPushButton(' Excluir')
    main_window.delete_pfs_btn.clicked.connect(main_window.delete_pfs_profile)
    profile_layout.addWidget(main_window.delete_pfs_btn)

    profiles_layout.addLayout(profile_layout)

    main_window.pfs_params_table = QTableWidget()
    main_window.pfs_params_table.setColumnCount(3)
    main_window.pfs_params_table.setHorizontalHeaderLabels(['Parâmetro', 'Valor', 'Ações'])
    main_window.pfs_params_table.horizontalHeader().setStretchLastSection(True)
    main_window.pfs_params_table.setAlternatingRowColors(False)
    main_window.pfs_params_table.setStyleSheet('''
        QTableWidget {
            background-color: #1a1a1a;
            color: white;
            gridline-color: #333;
        }
        QTableWidget::item {
            background-color: #1a1a1a;
            color: white;
            border: 1px solid #333;
        }
        QTableWidget::item:selected {
            background-color: #2a2a2a;
            color: white;
        }
        QHeaderView::section {
            background-color: #2a2a2a;
            color: white;
            border: 1px solid #333;
            padding: 4px;
        }
    ''')
    main_window.pfs_params_table.setMinimumHeight(250)
    profiles_layout.addWidget(main_window.pfs_params_table, 1)

    profiles_group.setLayout(profiles_layout)
    layout.addWidget(profiles_group)

    # Profile Info Group
    info_group = QGroupBox('Informações do Perfil')
    info_layout = QVBoxLayout()

    main_window.pfs_info_text = QTextEdit()
    main_window.pfs_info_text.setMaximumHeight(100)
    main_window.pfs_info_text.setReadOnly(True)
    info_layout.addWidget(main_window.pfs_info_text)

    info_group.setLayout(info_layout)
    layout.addWidget(info_group)

    tab.setLayout(layout)
    main_window.tab_widget.addTab(tab, ' Perfis Camêra Bassler')

    return tab
