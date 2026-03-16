"""Dialog for viewing history images."""

from pathlib import Path
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QScrollArea
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt


class HistoryImageDialog(QDialog):
    """Dialog for viewing historic inspection results with images."""

    def __init__(self, folder: Path, parent=None):
        """Initialize history image viewer.
        
        Args:
            folder: Path to result folder containing images
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle(f'Visualizar histórico - {folder.name}')
        layout = QVBoxLayout()

        def add_image(path: Path, title: str):
            """Add image to layout."""
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
