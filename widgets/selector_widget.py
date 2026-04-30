from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QPushButton
from PySide6.QtCore import Signal, Qt

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPlainTextEdit, QPushButton

class SelectorWidget(QWidget):
    action_clicked = Signal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        layout.setContentsMargins(5, 5, 5, 5) 
        layout.setSpacing(10)

        self.label = QLabel("Selected Regions:")

        self.display = QPlainTextEdit()
        self.display.setReadOnly(True)
        self.display.setMaximumHeight(50)
        
        self.btn_action = QPushButton("Process Data")
        self.btn_action.clicked.connect(self.action_clicked.emit)
        
        layout.addWidget(self.label)
        layout.addWidget(self.display)
        layout.addWidget(self.btn_action)

        layout.addStretch(1) 

    def update_display(self, names_list):
        """Updates the text box with the current selection"""
        self.display.setPlainText("\n".join(names_list))