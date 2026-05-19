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

        # Date State
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
        
        self.selector.clear_news()
        self.selector.clear_topics()
        self.selector.set_silhouette_score("-")
        self.selector.set_status("Procesiram podatke ...")
        self.selector.set_controls_enabled(False)

        QApplication.processEvents()

        try:
            date_range = f"{self.current_start.toString(Qt.ISODate)} to {self.current_end.toString(Qt.ISODate)}"
            self.log(f"-"*25)
            self.log(f"Started getting topics from {len(self.selected_regions)} regions | Period: {date_range}")
            
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

            self.selector.update_topics(df_topic, len(df_topic))
            
            if self.selector.topic_dropdown.count() > 1:
                self.selector.set_status("Pripravljeno. Izberi topic in klikni GET NEWS.")
            else:
                self.selector.set_status("Ni najdenih tem z novicami za izbrano obdobje.")
                
            self.log("Displayed formatted topics in dropdown selection window.")
        
        except Exception as e:
            self.selector.set_status(f"Napaka pri procesiranju: {e}")
            self.log(f"ERROR: {e}")

        finally:
            self.selector.set_controls_enabled(True)
    
    def handle_topic_selection(self, topic_name):
        self.selector.clear_news()
        self.selector.set_silhouette_score("-")
        self.selector.set_status(f"Izbran topic: {topic_name}. Klikni GET NEWS.")
        self.active_topic = topic_name
        self.log(f"Active topic set to: {topic_name}")
        self.selector.set_active_topic(topic_name)

    def handle_regression_selection(self, regression_name):
        self.active_reg = regression_name

    def handle_get_news(self):
        if self.active_topic is None:
            self.log("Najprej izberi topic.")
            return
        self.log("-" * 25)
        self.log("Analyzing chiter-chatter")

        # --- FEATURE UPDATE: Cap cluster counts and articles automatically ---
        total_news_available = self.selector.topic_counts.get(self.active_topic, 0)
        cluster_count = self.selector.get_cluster_count()
        article_count = self.selector.get_article_count()

        # Enforce that (cluster_count * article_count) <= total_news_available
        if total_news_available > 0 and (cluster_count * article_count) > total_news_available:
            self.log(f"Requested configuration ({cluster_count}x{article_count}) exceeds total available news ({total_news_available}). Auto-adjusting...")
            if total_news_available == 1:
                cluster_count = 1
                article_count = 1
            else:
                # Keep requested clusters if possible, reduce articles per cluster
                cluster_count = min(cluster_count, total_news_available)
                article_count = max(1, total_news_available // cluster_count)
            
            # Sync back values visually into the UI widgets
            self.selector.cluster_count.setValue(cluster_count)
            self.selector.article_count.setValue(article_count)

        if total_news_available <= 1 or self.active_reg == "None":
            pridobi_pomembnost_besed = False
            regression = None
        else:
            pridobi_pomembnost_besed = True
            regression = self.active_reg

        self.log(f"Using {cluster_count} clusters")
        self.log(f"Showing {article_count} articles per cluster")

        result = self.dataBroker.topNnovicIzTopica(topics=self.active_topic, st_gruc=cluster_count, st_clankov_na_gruco=article_count,
                                                 pridobi_pomembnosti_besed=pridobi_pomembnost_besed, regression=regression )

        if result is None:
            self.log("Ni rezultata.")
            return

        self.active_news_and_imporances = result
        novice_df, importance_map, silhouette = result
        self.selector.set_silhouette_score(silhouette)
        self.selector.display_news(novice_df, importance_map)

        self.log("Chiter-chatter fully analysed")

    def handle_auto_cluster(self):
        if self.active_topic is None:
            self.log("Najprej izberi topic.")
            return

        total_news_available = self.selector.topic_counts.get(self.active_topic, 0)
        if total_news_available <= 1:
            self.log("Not enough news to run auto clustering.")
            return

        self.log("Automatically choosing number of clusters...")
        # Cap max evaluation search grid by total available articles safely
        max_search_k = min(10, total_news_available)
        min_search_k = min(2, max_search_k)

        if min_search_k == max_search_k:
            best_k, score = min_search_k, 0.0
        else:
            best_k, score = self.dataBroker.chooseOptimalnoSteviloGruc(self.active_topic, min_k=min_search_k, max_k=max_search_k)
            
        self.selector.cluster_count.setValue(best_k)
        self.selector.set_silhouette_score(score)
        
        self.handle_get_news()
        self.log(f"Auto selected {best_k} clusters.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='light_blue.xml', invert_secondary=True)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())