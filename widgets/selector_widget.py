from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPlainTextEdit, QPushButton, QDateEdit, 
                             QRadioButton, QButtonGroup, QFrame, QSpinBox,
                             QComboBox)
from PySide6.QtCore import Signal, Qt, QDate
from widgets.detail_window_dialog import NewsDetailWindow

class SelectorWidget(QWidget):
    action_clicked = Signal() 
    date_changed = Signal(QDate, QDate)
    topic_selected = Signal(str)
    get_news_clicked = Signal()
    regression_selected = Signal(str)
    auto_cluster_clicked = Signal()

    def __init__(self, min_date_str=None, max_date_str=None):
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5) 
        self.main_layout.setSpacing(10)

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

        self.display = QPlainTextEdit(readOnly=True)
        self.display.setMaximumHeight(60)
        self.main_layout.addWidget(QLabel("Selected Regions:"))
        self.main_layout.addWidget(self.display)
        
        self.btn_action = QPushButton("Process Data")
        self.btn_action.clicked.connect(self.action_clicked.emit)
        self.status_label = QLabel("Pripravljeno.")
        self.main_layout.addWidget(self.status_label)
        self.main_layout.addWidget(self.btn_action)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        self.main_layout.addWidget(line)

        self.method_group = QButtonGroup(self)
        radio_layout = QHBoxLayout()
        
        # NOTE: Če spreminjaš tu imena jih rabiš tudi drugje v kodi
        methods = [("auto-reg", True), ("None", False), ("clustercenter", False), ("logreg", False), ("logregcv", False)] #autoreg default
        for name, checked in methods:
            rb = QRadioButton(name)
            rb.setChecked(checked)
            self.method_group.addButton(rb)
            radio_layout.addWidget(rb)
            rb.toggled.connect(lambda checked, n=name: self.handle_radio_toggle(checked, n))
        
        self.main_layout.addLayout(radio_layout)

        # --- Dynamic Topics Area ---
        self.topic_label = QLabel("Top Topics:")
        self.main_layout.addWidget(self.topic_label)

        self.topic_dropdown = QComboBox()
        self.topic_dropdown.activated.connect(self.handle_dropdown_topic)
        self.main_layout.addWidget(self.topic_dropdown)
        
        self.topic_container = QVBoxLayout()
        self.topic_container.setSpacing(2)
        self.main_layout.addLayout(self.topic_container)
        
        self.selected_topic = None

        #za nastavitve gruč
        self.cluster_count = QSpinBox()
        self.cluster_count.setMinimum(2)
        self.cluster_count.setMaximum(10)
        self.cluster_count.setValue(3)
        self.cluster_count.setEnabled(True)

        cluster_layout = QHBoxLayout()

        cluster_layout.addWidget(QLabel("Število gruč:"))
        cluster_layout.addWidget(self.cluster_count)

        self.btn_auto_clusters = QPushButton("Auto")
        self.btn_auto_clusters.setEnabled(False)
        self.btn_auto_clusters.clicked.connect(self.auto_cluster_clicked.emit)
        cluster_layout.addWidget(self.btn_auto_clusters)

        self.main_layout.addLayout(cluster_layout)

        self.silhouette_label = QLabel("Silhouette score: -")
        self.main_layout.addWidget(self.silhouette_label)


        # --- Get News Button ---
        self.btn_get_news = QPushButton("Get News")
        self.btn_get_news.setEnabled(False)
        self.btn_get_news.clicked.connect(self.handle_get_news)
        self.main_layout.addWidget(self.btn_get_news)

        self.news_layout = QVBoxLayout()
        self.news_layout.setSpacing(10)
        self.main_layout.addLayout(self.news_layout)

        self.main_layout.addStretch(1)

    def update_topics(self, topic_series, max_n):
        self.clear_topics() # Clean start
        
        #top_topics = topic_series.head(max_n).index.tolist()
        all_topics = topic_series.index.tolist()
        self.topic_dropdown.clear()
        self.topic_dropdown.addItem("Izberi topic ...")
        self.topic_dropdown.addItems(all_topics)
        top_topics = all_topics[:max_n]

        for topic in top_topics:
            btn = QPushButton(topic)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)

            btn.clicked.connect(lambda chk, t=topic: self.topic_selected.emit(t))
            self.topic_container.addWidget(btn)

    def clear_topics(self):
        self.selected_topic = None
        self.btn_get_news.setEnabled(False)
        self.topic_dropdown.clear()
        while self.topic_container.count():
            child = self.topic_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        

    def set_active_topic(self, topic_name):
        self.selected_topic = topic_name
        self.btn_get_news.setEnabled(True)

    def handle_get_news(self):
        self.get_news_clicked.emit()

    def emit_range(self):
        self.date_changed.emit(self.start_date.date(), self.end_date.date())

    def update_display(self, names_list):
        self.display.setPlainText("\n".join(names_list))

    def get_cluster_count(self):
        return self.cluster_count.value()
    
    def handle_dropdown_topic(self, index):
        topic_name = self.topic_dropdown.itemText(index)
        if topic_name or topic_name == "Izberi topic ...":
            self.topic_selected.emit(topic_name)
    
    def handle_radio_toggle(self, is_checked, name):
        if is_checked:
            self.regression_selected.emit(name)
            self.cluster_count.setEnabled(True)

    def clear_news(self):
        while self.news_layout.count():
            item = self.news_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def set_silhouette_score(self, score):
        if score is None or score == "-":
            self.silhouette_label.setText("Silhouette score: -")
        else:
            self.silhouette_label.setText(f"Silhouette score: {float(score):.3f}")

    def set_status(self, text):
        self.status_label.setText(text)

    def set_controls_enabled(self, enabled):
        self.btn_action.setEnabled(enabled)
        self.btn_get_news.setEnabled(enabled and self.selected_topic is not None)
        self.cluster_count.setEnabled(enabled)
        self.btn_auto_clusters.setEnabled(False)
        self.start_date.setEnabled(enabled)
        self.end_date.setEnabled(enabled)

    def display_news(self, df, cluster_word_map):
        self.clear_news()

        if cluster_word_map is None:
            cluster_word_map = {}

        grouped = df.groupby("cluster_label")

        for cluster_id, cluster_df in grouped:

            cluster_size = cluster_df.iloc[0].get("cluster_size", "?")

            cluster_header = QLabel(
                f"<h3>Gruča {cluster_id +1} "
                f"(št. člankov: {cluster_size})</h3>"
            )

            self.news_layout.addWidget(cluster_header)

            for _, row in cluster_df.iterrows():

                news_item_frame = QFrame()
                news_item_frame.setFrameShape(QFrame.StyledPanel)

                item_layout = QVBoxLayout(news_item_frame)

                title_label = QLabel(
                    f"<b><a href='#'>{row['title']}</a></b>"
                )

                title_label.setWordWrap(True)

                importance_list = cluster_word_map.get(cluster_id, [])

                title_label.linkActivated.connect(
                    lambda _, r=row, imp=importance_list:
                    self.open_detail_window(
                        r['title'],
                        r['content'],
                        imp
                    )
                )

                content_preview = str(row['content'])[:250] + "..."

                content_label = QLabel(content_preview)
                content_label.setWordWrap(True)

                item_layout.addWidget(title_label)
                item_layout.addWidget(content_label)

                self.news_layout.addWidget(news_item_frame)

        """
        for _, row in df.iterrows():
            news_item_frame = QFrame()
            item_layout = QVBoxLayout(news_item_frame)
            
            title_label = QLabel(f"<b><a href='#'>{row['title']}</a></b>")
            title_label.setWordWrap(True)
            
            cluster_id = row.get('cluster_label')
            importance_list = cluster_word_map.get(cluster_id)
            if importance_list is None:
                importance_list = []

            title_label.linkActivated.connect( # Open new window with news
                lambda _, r=row, imp=importance_list: self.open_detail_window(r['title'], r['content'], imp)
            )

            content_label = QLabel(str(row['content'])[:250] + "...")
            content_label.setWordWrap(True)

            item_layout.addWidget(title_label)
            item_layout.addWidget(content_label)
            self.news_layout.addWidget(news_item_frame)"""

    def open_detail_window(self, title, content, importance_list):
        self.detail_window = NewsDetailWindow(title, content, importance_list, self)
        self.detail_window.show()