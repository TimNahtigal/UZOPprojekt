from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPlainTextEdit, QPushButton, QDateEdit)
from PySide6.QtCore import Signal, Qt, QDate

class SelectorWidget(QWidget):
    action_clicked = Signal() # No longer needs to send dates, controller has them
    date_changed = Signal(QDate, QDate) # Notify controller of changes

    def __init__(self, min_date_str=None, max_date_str=None):
        super().__init__()
        layout = QVBoxLayout(self)
        
        abs_min = QDate.fromString(min_date_str, Qt.ISODate) if min_date_str else QDate(2000, 1, 1)
        abs_max = QDate.fromString(max_date_str, Qt.ISODate) if max_date_str else QDate.currentDate()

        date_layout = QHBoxLayout()
        self.start_date = QDateEdit(calendarPopup=True, date=abs_min)
        self.end_date = QDateEdit(calendarPopup=True, date=abs_max)
        
        for d in [self.start_date, self.end_date]:
            d.setDisplayFormat("yyyy-MM-dd")
            d.setDateRange(abs_min, abs_max)
            # Emit our custom signal whenever the underlying QDateEdit changes
            d.dateChanged.connect(self.emit_range)

        # Internal UI constraints
        self.start_date.dateChanged.connect(self.end_date.setMinimumDate)
        self.end_date.dateChanged.connect(self.start_date.setMaximumDate)

        date_layout.addWidget(QLabel("From:"))
        date_layout.addWidget(self.start_date)
        date_layout.addWidget(QLabel("To:"))
        date_layout.addWidget(self.end_date)
        
        self.display = QPlainTextEdit(readOnly=True)
        self.display.setMaximumHeight(80)
        
        self.btn_action = QPushButton("Process Data")
        self.btn_action.clicked.connect(self.action_clicked.emit)
        
        layout.addLayout(date_layout)
        layout.addWidget(QLabel("Selected Regions:"))
        layout.addWidget(self.display)
        layout.addWidget(self.btn_action)
        layout.addStretch(1)

    def emit_range(self):
        """Helper to send both dates at once to the controller."""
        self.date_changed.emit(self.start_date.date(), self.end_date.date())

    def update_display(self, names_list):
        self.display.setPlainText("\n".join(names_list))