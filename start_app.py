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

        layout = QHBoxLayout(self)

        self.console = ConsoleWidget()
        self.map = MapWidget()
        self.selector = SelectorWidget()

        layout.addWidget(self.console, stretch=1)
        layout.addWidget(self.map, stretch=2)
        layout.addWidget(self.selector, stretch=1)

        self.map.region_selected.connect(self.on_selection_changed)
        self.selector.action_clicked.connect(self.on_button_pressed)

    def on_selection_changed(self, selected_list):
        self.console.log(f"Selection updated: {len(selected_list)} regions selected")
        self.selector.update_display(selected_list)

    def on_button_pressed(self):
        content = self.selector.display.toPlainText()
        regions = content.split('\n') if content else []
        self.console.log(f"Processing {len(regions)} regions...")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
    


