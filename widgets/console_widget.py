import re
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit

class ConsoleWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        self.label = QLabel("Console Output:")
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet("""
            font-family: 'Courier New';
        """)
        
        layout.addWidget(self.label)
        layout.addWidget(self.output)
        
    def log(self, message):
        # 1. Match unescaped brackets and wrap the inner text in HTML color tags, dropping the brackets
        # Pattern: (?<!\\)\[ (unescaped [) -> group 1 (content) -> (?<!\\)\] (unescaped ])
        processed = re.sub(
            r'(?<!\\)\[([^\]]+)(?<!\\)\]', 
            r'<span style="color: #e65100;">\1</span>', 
            message
        )
        
        # 2. Clean up any escaped brackets (e.g., changing "\[" back to just "[")
        processed = processed.replace(r'\[', '[').replace(r'\]', ']')
        
        # 3. Use append() which natively renders basic HTML subsets
        self.output.append(f"> {processed}")