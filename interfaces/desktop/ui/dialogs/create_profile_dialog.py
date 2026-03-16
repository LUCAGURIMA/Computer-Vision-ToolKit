"""Dialog for creating new camera profiles."""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit


class CreateProfileDialog(QDialog):
    """Dialog for creating a new camera profile."""

    def __init__(self, parent=None):
        """Initialize create profile dialog.
        
        Args:
            parent: Parent widget
        """
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
        """Get entered profile name.
        
        Returns:
            Trimmed profile name
        """
        return self.name_input.text().strip()
