from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget

class SelectorWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        self.label = QLabel("Region Selection:")
        self.list = QListWidget()
        
        regions = [
            "Gorenjska", "Goriška", "Jugovzhodna Slovenija", 
            "Koroška", "Obalno-kraška", "Osrednjeslovenska", 
            "Podravska", "Pomurska", "Savinjska", 
            "Spodnjeposavska", "Srednjeposavska", "Zasavska"
        ]
        self.list.addItems(regions)
        
        layout.addWidget(self.label)
        layout.addWidget(self.list)