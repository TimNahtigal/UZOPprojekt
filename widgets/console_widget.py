import re
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton

class ConsoleWidget(QWidget):
    def __init__(self):
        super().__init__()
        # Main layout is vertical
        layout = QVBoxLayout(self)
        
        # --- Header Horizontal Layout ---
        header_layout = QHBoxLayout()
        
        self.label = QLabel("Console Output:")
        
        self.clear_btn = QPushButton("Počisti")
        self.clear_btn.clicked.connect(self.clear_console)
        # Optional: styling to make it look clean next to the label
        self.clear_btn.setStyleSheet("""
            QPushButton {
                padding: 2px 10px;
                font-size: 11px;
            }
        """)
        
        header_layout.addWidget(self.label)
        header_layout.addStretch()  
        header_layout.addWidget(self.clear_btn)
        
        # --- Add components to main layout ---
        layout.addLayout(header_layout) # Add the row containing label and button
        
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet("""
            font-family: 'Courier New';
        """)
        
        layout.addWidget(self.output)
        
    def clear_console(self):
        """Clears all text from the console window."""
        self.output.clear()
        
    def log(self, message):
        # 1. Match unescaped brackets and wrap the inner text in HTML color tags, dropping the brackets
        processed = re.sub(
            r'(?<!\\)\[([^\]]+)(?<!\\)\]', 
            r'<span style="color: #e65100;">\1</span>', 
            message
        )
        
        # 2. Clean up any escaped brackets
        processed = processed.replace(r'\[', '[').replace(r'\]', ']')
        
        # 3. Use append() which natively renders basic HTML subsets
        self.output.append(f"> {processed}")