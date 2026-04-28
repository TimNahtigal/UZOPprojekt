import sys
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout
from widgets.console_widget import ConsoleWidget
from widgets.map_widget import MapWidget
from widgets.selector_widget import SelectorWidget

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modular Slovenia Data App")
        self.resize(1100, 600)

        # Main Layout
        layout = QHBoxLayout(self)

        # Instantiate our custom widgets
        self.console = ConsoleWidget()
        self.map = MapWidget()
        self.selector = SelectorWidget()

        # Add them to the layout with stretch factors
        layout.addWidget(self.console, stretch=1)
        layout.addWidget(self.map, stretch=2)
        layout.addWidget(self.selector, stretch=1)

        # Example of cross-widget interaction
        self.selector.list.itemClicked.connect(self.on_region_selected)

    def on_region_selected(self, item):
        self.console.log(f"Selected region: {item.text()}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
    


