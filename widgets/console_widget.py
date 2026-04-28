from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit

class ConsoleWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        self.label = QLabel("Console Output:")
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet("""
            background-color: #1e1e1e; 
            color: #00ff00; 
            font-family: 'Courier New';
        """)
        
        layout.addWidget(self.label)
        layout.addWidget(self.output)
        
    def log(self, message):
        self.output.append(f"> {message}")