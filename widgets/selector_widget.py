import re
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPlainTextEdit, QPushButton, QDateEdit, 
                             QRadioButton, QButtonGroup, QFrame, QSpinBox,
                             QComboBox, QScrollArea)
from PySide6.QtCore import Signal, Qt, QDate
from widgets.detail_window_dialog import NewsDetailWindow

class SelectorWidget(QWidget):
    action_clicked = Signal() 
    date_changed = Signal(QDate, QDate)
    topic_selected = Signal(str)
    get_news_clicked = Signal()
    regression_selected = Signal(str)
    auto_cluster_clicked = Signal()
    reset_clicked = Signal()

    def __init__(self, min_date_str=None, max_date_str=None):
        super().__init__()
        self.selected_topic = None
        self.topic_counts = {}  # Tracks article counts per topic string mapping
        
        self.setFixedWidth(500)
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0) 
        
        main_scroll = QScrollArea(self)
        main_scroll.setWidgetResizable(True)
        main_scroll.setFrameShape(QFrame.NoFrame) 

        main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        main_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        scroll_content = QWidget()
        main_scroll.setWidget(scroll_content)
        
        self.main_layout = QVBoxLayout(scroll_content)
        self.main_layout.setContentsMargins(5, 5, 5, 5) 
        self.main_layout.setSpacing(10)
        
        outer_layout.addWidget(main_scroll)

        abs_min = QDate.fromString(min_date_str, Qt.ISODate) if min_date_str else QDate(2000, 1, 1)
        abs_max = QDate.fromString(max_date_str, Qt.ISODate) if max_date_str else QDate.currentDate()

        self.btn_reset = QPushButton("Počisti")
        self.btn_reset.clicked.connect(self.reset_clicked.emit)
        top_row = QHBoxLayout()
        top_row.addStretch(1)
        self.btn_reset.setFixedWidth(100)

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
        date_layout.addStretch(1)
        date_layout.addWidget(self.btn_reset)

        self.display = QPlainTextEdit(readOnly=True)
        self.display.setMaximumHeight(60)
        self.main_layout.addWidget(QLabel("Izbrane regije:"))
        self.main_layout.addWidget(self.display)
        
        self.btn_action = QPushButton("Process Data")
        self.btn_action.clicked.connect(self.action_clicked.emit)
        self.status_label = QLabel("Pripravljeno. Izberi <span style='color: #e65100;'>regijo</span> in <span style='color: #e65100;'>obdobje</span>, nato klikni <span style='color: #e65100;'>PROCESS DATA</span>.")
        self.main_layout.addWidget(self.status_label)
        self.main_layout.addWidget(self.btn_action)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        self.main_layout.addWidget(line)

        # --- Dynamic Topics Area ---
        self.topic_label = QLabel("Seznam tem:")
        self.main_layout.addWidget(self.topic_label)

        self.topic_dropdown = QComboBox()
        self.topic_dropdown.activated.connect(self.handle_dropdown_topic)
        self.main_layout.addWidget(self.topic_dropdown)

        self.cluster_count = QSpinBox()
        self.cluster_count.setMinimum(1)
        self.cluster_count.setMaximum(10)
        self.cluster_count.setValue(3)
        self.cluster_count.setEnabled(True)

        cluster_layout = QHBoxLayout()
        cluster_layout.addWidget(QLabel("Število gruč:"))
        cluster_layout.addWidget(self.cluster_count)

        self.article_count = QSpinBox()
        self.article_count.setMinimum(1)
        self.article_count.setMaximum(20)
        self.article_count.setValue(3)

        cluster_layout.addWidget(QLabel("Člankov na gručo:"))
        cluster_layout.addWidget(self.article_count)

        self.btn_auto_clusters = QPushButton("Auto")
        self.btn_auto_clusters.setEnabled(False)
        self.btn_auto_clusters.clicked.connect(self.auto_cluster_clicked.emit)
        cluster_layout.addWidget(self.btn_auto_clusters)

        self.main_layout.addLayout(cluster_layout)

        reset_clicked = Signal()

        # --- Radio Buttons Layout ---
        self.method_group = QButtonGroup(self)
        self.radio_buttons = []
        radio_layout = QHBoxLayout()
        
        methods = [("auto-reg", True), ("None", False), ("clustercenter", False), ("logreg", False), ("logregcv", False)] 
        for name, checked in methods:
            rb = QRadioButton(name)
            rb.setChecked(checked)
            self.method_group.addButton(rb)
            radio_layout.addWidget(rb)
            self.radio_buttons.append(rb)
            rb.toggled.connect(lambda checked, n=name: self.handle_radio_toggle(checked, n))
        
        self.main_layout.addLayout(radio_layout)

        self.silhouette_label = QLabel("Silhouette score: -")
        self.main_layout.addWidget(self.silhouette_label)

        self.btn_get_news = QPushButton("Get News")
        self.btn_get_news.setEnabled(False)
        self.btn_get_news.clicked.connect(self.handle_get_news)
        self.main_layout.addWidget(self.btn_get_news)

        self.news_container = QWidget()
        self.news_layout = QVBoxLayout(self.news_container)
        self.news_layout.setSpacing(10)

        self.news_scroll = QScrollArea()
        self.news_scroll.setWidgetResizable(True)
        self.news_scroll.setWidget(self.news_container)
        self.news_scroll.setMinimumHeight(400)

        self.main_layout.addWidget(self.news_scroll)
        self.main_layout.addStretch(1)

    def update_topics(self, topic_series, max_n):
        self.clear_topics() 
        self.topic_counts = topic_series.to_dict()
        
        all_topics = topic_series.index.tolist()
        self.topic_dropdown.clear()
        
        self.topic_dropdown.addItem("Izberi topic ...", None)
        
        for topic in all_topics:
            if topic_series[topic] <= 0:
                continue

            clean_name = topic.replace("_", " ").replace("-", " ")
            clean_name = re.sub(r'[^\w\s]', '', clean_name)
            clean_name = clean_name.strip().capitalize()
            
            self.topic_dropdown.addItem(f"{clean_name} ({int(topic_series[topic])})", topic)

    def clear_topics(self):
        self.selected_topic = None
        self.topic_counts = {}
        self.btn_get_news.setEnabled(False)
        self.btn_auto_clusters.setEnabled(False)
        self.topic_dropdown.clear()
        self.cluster_count.setMaximum(10)  # Reset to fallback maximum
        self.set_silhouette_score("-")     # Clear score tracking fields
        
    def set_active_topic(self, topic_name):
        if topic_name is None:
            self.selected_topic = None
            self.btn_get_news.setEnabled(False)
            self.btn_auto_clusters.setEnabled(False)
            self.cluster_count.setMaximum(10)  # Reset default maximum
            self._toggle_regression_controls(True)
            return

        self.selected_topic = topic_name
        self.btn_get_news.setEnabled(True)
        
        num_news = self.topic_counts.get(topic_name, 0)
        
        if num_news <= 1:
            self.btn_auto_clusters.setEnabled(False)
            self.cluster_count.setMaximum(1)
            self.cluster_count.setValue(1)
            self.cluster_count.setEnabled(False)
            self._toggle_regression_controls(False)
        else:
            self.btn_auto_clusters.setEnabled(True)
            self.cluster_count.setEnabled(True)
            # Cap the max clusters dynamically so it cannot exceed the article count
            self.cluster_count.setMaximum(num_news)
            
            # Adjust value downward if the previous selection is now out-of-bounds
            if self.cluster_count.value() > num_news:
                self.cluster_count.setValue(num_news)
                
            self._toggle_regression_controls(True)

        for idx in range(self.topic_dropdown.count()):
            if self.topic_dropdown.itemData(idx, Qt.UserRole) == topic_name:
                self.topic_dropdown.setCurrentIndex(idx)
                break

    def _toggle_regression_controls(self, enabled):
        """Helper to manage regression options depending on topic news counts."""
        num_news = self.topic_counts.get(self.selected_topic, 0) if self.selected_topic else 0
        
        for rb in self.radio_buttons:
            if not enabled:
                rb.setEnabled(False)
            else:
                # If total news is less than 5, specifically isolate and disable logregcv
                if rb.text() == "logregcv" and num_news < 5:
                    rb.setEnabled(False)
                    # If logregcv was previously selected, automatically reset back to auto-reg safely
                    if rb.isChecked():
                        for fallback_rb in self.radio_buttons:
                            if fallback_rb.text() == "auto-reg":
                                fallback_rb.setChecked(True)
                                break
                else:
                    rb.setEnabled(True)

    def handle_get_news(self):
        # Clear/Reset visual layout metrics display text immediately when clicked
        self.set_silhouette_score("-")
        self.get_news_clicked.emit()

    def emit_range(self):
        self.date_changed.emit(self.start_date.date(), self.end_date.date())

    def update_display(self, names_list):
        self.display.setPlainText("\n".join(names_list))

    def get_cluster_count(self):
        return self.cluster_count.value()
    
    def get_article_count(self):
        return self.article_count.value()
    
    def handle_dropdown_topic(self, index):
        self.clear_news()
        raw_topic_name = self.topic_dropdown.itemData(index, Qt.UserRole)
        if not raw_topic_name:
            self.set_active_topic(None)
            return
        self.topic_selected.emit(raw_topic_name)
    
    def handle_radio_toggle(self, is_checked, name):
        if is_checked:
            self.regression_selected.emit(name)

    def clear_news(self):
        while self.news_layout.count():
            item = self.news_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def set_silhouette_score(self, score):
        if score is None or score == "-":
            self.silhouette_label.setText("Silhouette score: -")
            self.silhouette_label.setStyleSheet("")
            return
        self.silhouette_label.setText(
            f'Silhouette score: <b>{float(score):.3f}</b>'
        )
        self.silhouette_label.setTextFormat(Qt.RichText)
        self.silhouette_label.setStyleSheet(f"color: {"#e65100"}; font-weight: bold;")

    def set_status(self, text):
        self.status_label.setText(text)

    def set_controls_enabled(self, enabled):
        self.btn_action.setEnabled(enabled)
        self.btn_get_news.setEnabled(enabled and self.selected_topic is not None)
        
        num_news = self.topic_counts.get(self.selected_topic, 0) if self.selected_topic else 0
        if num_news > 1:
            self.cluster_count.setEnabled(enabled)
            self.btn_auto_clusters.setEnabled(enabled and self.selected_topic is not None)
            self._toggle_regression_controls(enabled)
        else:
            self.cluster_count.setEnabled(False)
            self.btn_auto_clusters.setEnabled(False)
            self._toggle_regression_controls(False)

    def display_news(self, df, cluster_word_map):
        self.clear_news()
        if df is None or df.empty:
            return

        if cluster_word_map is None:
            cluster_word_map = {}

        grouped = df.groupby("cluster_label")
        for cluster_id, cluster_df in grouped:
            cluster_size = cluster_df.iloc[0].get("cluster_size", "?")
            cluster_header = QLabel(f"<h3>Gruča {cluster_id + 1} (št. člankov: {cluster_size})</h3>")
            self.news_layout.addWidget(cluster_header)

            for _, row in cluster_df.iterrows():
                news_item_frame = QFrame()
                news_item_frame.setFrameShape(QFrame.StyledPanel)
                item_layout = QVBoxLayout(news_item_frame)

                title_label = QLabel(f"<a href='#' style='color:  #e65100; font-weight: bold;'>{row['title']}</a>")
                title_label.setWordWrap(True)

                importance_list = cluster_word_map.get(cluster_id, [])
                title_label.linkActivated.connect(
                    lambda _, r=row, imp=importance_list: self.open_detail_window(r['title'], r['content'], imp)
                )

                content_preview = str(row['content'])[:250] + "..."
                content_label = QLabel(content_preview)
                content_label.setWordWrap(True)

                item_layout.addWidget(title_label)
                item_layout.addWidget(content_label)
                self.news_layout.addWidget(news_item_frame)

    def open_detail_window(self, title, content, importance_list):
        self.detail_window = NewsDetailWindow(title, content, importance_list, self)
        self.detail_window.show()