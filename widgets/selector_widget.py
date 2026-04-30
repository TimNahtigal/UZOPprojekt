from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPlainTextEdit, QPushButton, QDateEdit, 
                             QRadioButton, QButtonGroup, QFrame)
from PySide6.QtCore import Signal, Qt, QDate

class SelectorWidget(QWidget):
    action_clicked = Signal() 
    date_changed = Signal(QDate, QDate)
    topic_selected = Signal(str)  # New signal for when a topic button is clicked
    get_news_clicked = Signal(str, str) # Signals topic name and method

    def __init__(self, min_date_str=None, max_date_str=None):
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5) 
        self.main_layout.setSpacing(10)

        # --- Date Selection ---
        abs_min = QDate.fromString(min_date_str, Qt.ISODate) if min_date_str else QDate(2000, 1, 1)
        abs_max = QDate.fromString(max_date_str, Qt.ISODate) if max_date_str else QDate.currentDate()

        date_layout = QHBoxLayout()
        self.start_date = QDateEdit(calendarPopup=True, date=abs_min)
        self.end_date = QDateEdit(calendarPopup=True, date=abs_max)
        
        for d in [self.start_date, self.end_date]:
            d.setDisplayFormat("yyyy-MM-dd")
            d.setDateRange(abs_min, abs_max)
            d.dateChanged.connect(self.emit_range)

        date_layout.addWidget(QLabel("From:"))
        date_layout.addWidget(self.start_date)
        date_layout.addWidget(QLabel("To:"))
        date_layout.addWidget(self.end_date)
        self.main_layout.addLayout(date_layout)

        # --- Region Display ---
        self.display = QPlainTextEdit(readOnly=True)
        self.display.setMaximumHeight(60)
        self.main_layout.addWidget(QLabel("Selected Regions:"))
        self.main_layout.addWidget(self.display)
        
        # --- Process Button ---
        self.btn_action = QPushButton("Process Data")
        self.btn_action.clicked.connect(self.action_clicked.emit)
        self.main_layout.addWidget(self.btn_action)

        # --- Divider ---
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        self.main_layout.addWidget(line)

        # --- Radio Buttons (Methods) ---
        self.method_group = QButtonGroup(self)
        radio_layout = QHBoxLayout()
        
        methods = [("None", True), ("clustercenter", False), ("logreg", False), ("logregcv", False)]
        for name, checked in methods:
            rb = QRadioButton(name)
            rb.setChecked(checked)
            self.method_group.addButton(rb)
            radio_layout.addWidget(rb)
        
        self.main_layout.addLayout(radio_layout)

        # --- Dynamic Topics Area ---
        self.topic_label = QLabel("Top Topics:")
        self.main_layout.addWidget(self.topic_label)
        
        self.topic_container = QVBoxLayout()
        self.topic_container.setSpacing(2)
        self.main_layout.addLayout(self.topic_container)
        
        self.selected_topic = None

        # --- Get News Button ---
        self.btn_get_news = QPushButton("Get News")
        self.btn_get_news.setEnabled(False)
        self.btn_get_news.clicked.connect(self.handle_get_news)
        self.main_layout.addWidget(self.btn_get_news)

        self.main_layout.addStretch(1)

    def update_topics(self, topic_series, max_n):
        self.clear_topics() # Clean start
        
        top_topics = topic_series.head(max_n).index.tolist()
        for topic in top_topics:
            btn = QPushButton(topic)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)

            btn.clicked.connect(lambda chk, t=topic: self.topic_selected.emit(t))
            self.topic_container.addWidget(btn)

    def clear_topics(self):
        self.selected_topic = None
        self.btn_get_news.setEnabled(False)
        while self.topic_container.count():
            child = self.topic_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def set_active_topic(self, topic_name):
        self.selected_topic = topic_name
        self.btn_get_news.setEnabled(True)

    def handle_get_news(self):
        method = self.method_group.checkedButton().text()
        self.get_news_clicked.emit(self.selected_topic, method)

    def emit_range(self):
        self.date_changed.emit(self.start_date.date(), self.end_date.date())

    def update_display(self, names_list):
        self.display.setPlainText("\n".join(names_list))