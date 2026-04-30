import sys
import sqlite3
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout
from PySide6.QtCore import Qt, QDate
from widgets.console_widget import ConsoleWidget
from widgets.map_widget import MapWidget
from widgets.selector_widget import SelectorWidget
import datafetch

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_regions = set()
        
        # 1. New Date State
        self.current_start = QDate()
        self.current_end = QDate()
        
        # Database Setup
        connection = sqlite3.connect('final_data/novice.db')
        connection.execute("PRAGMA foreign_keys = ON")
        self.dataBroker = datafetch.DataBroker(connection, random_seed=0, logger=self.log)
        start_str, end_str = self.get_date_range(connection)

        # Initialize state from DB strings
        self.current_start = QDate.fromString(start_str, Qt.ISODate)
        self.current_end = QDate.fromString(end_str, Qt.ISODate)

        # UI Setup
        self.setWindowTitle("Modular Slovenia Data App")
        self.resize(1100, 600)
        layout = QHBoxLayout(self)

        self.console = ConsoleWidget()
        self.map = MapWidget()
        self.selector = SelectorWidget(start_str, end_str)

        layout.addWidget(self.console, stretch=1)
        layout.addWidget(self.map, stretch=2)
        layout.addWidget(self.selector, stretch=1)

        # Logic Mapping
        self.map.region_clicked.connect(self.handle_map_selection)
        
        # 2. Connect date changes to controller
        self.selector.date_changed.connect(self.handle_date_change)
        self.selector.action_clicked.connect(self.process_final_data)

    def log(self, obj):
        self.console.log(str(obj))

    def get_date_range(self, conn):
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT MIN(date), MAX(date) FROM novice")
            return cursor.fetchone()
        except sqlite3.OperationalError as e:
            self.log(f"DB Error: {e}")
            return None, None
        finally:
            cursor.close()

    def handle_date_change(self, start, end):
        # Update the controller's state
        self.current_start = start
        self.current_end = end
        self.log(f"Range updated: {start.toString(Qt.ISODate)} to {end.toString(Qt.ISODate)}")

    def handle_map_selection(self, region_name):
        if region_name in self.selected_regions:
            self.selected_regions.remove(region_name)
        else:
            self.selected_regions.add(region_name)
        
        sorted_list = sorted(list(self.selected_regions))
        self.map.set_highlighted_regions(self.selected_regions)
        self.selector.update_display(sorted_list)
        self.log(f"Selection updated: {len(sorted_list)} regions selected")

    def process_final_data(self):
        # Uses the state saved in the controller
        date_range = f"{self.current_start.toString(Qt.ISODate)} to {self.current_end.toString(Qt.ISODate)}"
        self.log(f"Final Process: {len(self.selected_regions)} regions | Period: {date_range}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())