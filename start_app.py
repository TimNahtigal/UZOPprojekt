import sys
import sqlite3
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout
from PySide6.QtCore import Qt, QDate
from widgets.console_widget import ConsoleWidget
from widgets.map_widget import MapWidget
from widgets.selector_widget import SelectorWidget
from datafetch import DataBroker, NoviceParametri
import datetime as dt
from qt_material import apply_stylesheet

MAX_NUMBER_OF_TOPICS_DISPLAYED = 3
NUMBER_OF_NEWS_TO_DISPLAY = 3

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_regions = set()
        self.active_topic = None
        self.active_reg = "auto-reg"
        self.active_news_and_imporances = (None, None)

        # 1. New Date State
        self.current_start = QDate()
        self.current_end = QDate()
        
        # Database Setup
        connection = sqlite3.connect('final_data/novice.db')
        connection.execute("PRAGMA foreign_keys = ON")
        self.dataBroker = DataBroker(connection, random_seed=0, logger=self.log)
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
        self.selector.date_changed.connect(self.handle_date_change)
        self.selector.action_clicked.connect(self.pridobi_topice)
        self.selector.get_news_clicked.connect(self.handle_get_news)
        self.selector.topic_selected.connect(self.handle_topic_selection)
        self.selector.regression_selected.connect(self.handle_regression_selection)

        self.selector.auto_cluster_clicked.connect(self.handle_auto_cluster)

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
        self.current_start = start
        self.current_end = end

    def handle_map_selection(self, region_name):
        if region_name in self.selected_regions:
            self.selected_regions.remove(region_name)
        else:
            self.selected_regions.add(region_name)
        
        sorted_list = sorted(list(self.selected_regions))
        self.map.set_highlighted_regions(self.selected_regions)
        self.selector.update_display(sorted_list)

    def pridobi_topice(self):
        self.active_topic = None 
        self.selector.clear_topics()

        date_range = f"{self.current_start.toString(Qt.ISODate)} to {self.current_end.toString(Qt.ISODate)}"
        self.log(f"-"*25)
        self.log(f"Started getting topics from {len(self.selected_regions)} regions | Period: {date_range}")
        
        # Novice od do + regije
        self.log("Gathering the gossip")
        q_start = self.current_start
        q_end = self.current_end
        start_dt = dt.datetime(q_start.year(), q_start.month(), q_start.day())
        end_dt = dt.datetime(q_end.year(), q_end.month(), q_end.day())
        params = NoviceParametri(
            start_time=start_dt,
            end_time=end_dt,
            regions=self.selected_regions
        )
        _ = self.dataBroker.pridobiNovice(params=params)
        self.log("Gossip gathered")

        self.log("Ranking the topics")
        df_topic = self.dataBroker.getPomembnostTopicov()
        self.log(str(df_topic.head()))

        self.selector.update_topics(df_topic, MAX_NUMBER_OF_TOPICS_DISPLAYED)
        self.log(f"Displayed top {MAX_NUMBER_OF_TOPICS_DISPLAYED} topics.")
    
    def handle_topic_selection(self, topic_name):
        self.active_topic = topic_name
        self.log(f"Active topic set to: {topic_name}")
        self.selector.set_active_topic(topic_name)

    def handle_regression_selection(self, regression_name):
        self.active_reg = regression_name

    def handle_get_news(self):
        self.log("-"*25)
        self.log("Analyzing chiter-chatter")
        #self.log(f"Fetching news for {self.active_topic} using {self.active_reg}...")
        pridobi_pomembnost_besed = True
        if self.active_reg == "None":
            pridobi_pomembnost_besed = False
            regession = None
        else:
            regession = self.active_reg

        cluster_count = self.selector.get_cluster_count()
        self.log(f"Using {cluster_count} clusters")
        most_representative_news_df = self.dataBroker.topNnovicIzTopica(self.active_topic, cluster_count, pridobi_pomembnost_besed, regession)
        self.active_news_and_imporances = most_representative_news_df
        self.selector.set_silhouette_score(most_representative_news_df[2])
        self.selector.display_news(most_representative_news_df[0], most_representative_news_df[1])

        self.log("Chiter-chatter fully analysed")
        #self.log(most_representative_news_df.head(3))
        #print(most_representative_news_df[0])

    def handle_auto_cluster(self):
        if self.active_topic is None:
            self.log("Najprej izberi topic.")
            return

        self.log("Automatically choosing number of clusters...")
        best_k, score = self.dataBroker.chooseOptimalnoSteviloGruc(self.active_topic, min_k=2, max_k=10)
        self.selector.cluster_count.setValue(best_k)
        self.selector.set_silhouette_score(score)
        
        self.handle_get_news()
        self.log(f"Auto selected {best_k} clusters.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='light_blue.xml', invert_secondary=True)
    #app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

