"""Theme management for desktop interface."""

from typing import Dict
from PyQt5.QtWidgets import QMainWindow, QWidget


class ThemeManager:
    """Manager for application theming."""

    DARK_THEME = 'dark'
    LIGHT_THEME = 'light'

    @staticmethod
    def get_dark_stylesheet() -> str:
        """Get dark theme stylesheet.
        
        Returns:
            CSS stylesheet for dark theme
        """
        return '''
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
            QGroupBox::indicator {
                width: 18px;
                height: 18px;
                background-color: #1a1a1a;
                border: 2px solid #888;
                border-radius: 3px;
            }
            QGroupBox::indicator:checked {
                background-color: #0d47a1;
                border: 2px solid #0d47a1;
            }
        '''

    @staticmethod
    def get_light_stylesheet() -> str:
        """Get light theme stylesheet.
        
        Returns:
            CSS stylesheet for light theme
        """
        return '''
            QMainWindow {
                background-color: #ffffff;
                color: #000000;
            }
            QPushButton {
                background-color: #f0f0f0;
                color: black;
                border: 1px solid #cccccc;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QLabel {
                color: #000000;
            }
            QTextEdit, QTableWidget {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #cccccc;
            }
        '''

    @staticmethod
    def apply_theme(widget: QWidget, theme: str = DARK_THEME):
        """Apply theme to widget.
        
        Args:
            widget: Widget to apply theme to
            theme: Theme name ('dark' or 'light')
        """
        if theme == ThemeManager.DARK_THEME:
            stylesheet = ThemeManager.get_dark_stylesheet()
        else:
            stylesheet = ThemeManager.get_light_stylesheet()
        
        if isinstance(widget, QMainWindow):
            widget.setStyleSheet(stylesheet)
