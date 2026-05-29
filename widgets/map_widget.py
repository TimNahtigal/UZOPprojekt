from PySide6.QtCore import Signal, QPointF, Qt
from PySide6.QtGui import QPainter, QPolygonF, QColor, QBrush, QPen
from PySide6.QtWidgets import QWidget, QPushButton # Imported QPushButton
import json
import os

class MapWidget(QWidget):
    region_clicked = Signal(str)  # Notify which region was clicked

    def __init__(self):
        super().__init__()
        self.regions_data = []
        self.highlighted = set()
        self.polygons_cache = []
        
        # --- Zoom & Pan Variables ---
        self.zoom_factor = 1.0
        self.pan_offset = QPointF(0, 0)
        self.last_mouse_pos = QPointF()
        self.is_panning = False
        
        self.load_nuts3_data()
        self.setMinimumSize(400, 400)
        self.setMouseTracking(True)

        # --- Recenter & Rezoom Floating Button ---
        self.reset_btn = QPushButton("Center", self)
        self.reset_btn.clicked.connect(self.reset_view)
        # Give it a nice clean styling so it looks great floating on the canvas
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.85);
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
                color: #333333;
            }
            QPushButton:hover {
                background-color: rgba(240, 240, 240, 0.95);
                border-color: #999999;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
        """)
        # Position it slightly away from top-left corner
        self.reset_btn.move(15, 15)

    def reset_view(self):
        """Resets zoom factors and translation variables back to default positions."""
        self.zoom_factor = 1.0
        self.pan_offset = QPointF(0, 0)
        self.update()

    def resizeEvent(self, event):
        """
        Keeps the floating button properly attached to its anchor position 
        if the widget layout scales or resizes.
        """
        super().resizeEvent(event)
        # Keeps it anchored at (15, 15) from top-left. 
        # (If you prefer top-right, use: self.width() - self.reset_btn.width() - 15)
        self.reset_btn.move(self.width() - self.reset_btn.width() - 15, 15)

    def set_highlighted_regions(self, regions_set):
        self.highlighted = regions_set
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            click_pos = event.position()
            for poly, name in reversed(self.polygons_cache):
                if poly.containsPoint(click_pos, Qt.OddEvenFill):
                    self.region_clicked.emit(name)
                    return
            
            self.is_panning = True
            self.last_mouse_pos = event.position()

    def mouseMoveEvent(self, event):
        if self.is_panning and event.buttons() & Qt.LeftButton:
            delta = event.position() - self.last_mouse_pos
            self.pan_offset += delta
            self.last_mouse_pos = event.position()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_panning = False

    def wheelEvent(self, event):
        zoom_step = 1.15 if event.angleDelta().y() > 0 else (1.0 / 1.15)
        new_zoom = self.zoom_factor * zoom_step
        if 0.5 <= new_zoom <= 20.0:
            mouse_pos = event.position()
            self.pan_offset = mouse_pos - (mouse_pos - self.pan_offset) * zoom_step
            self.zoom_factor = new_zoom
            self.update()

    def paintEvent(self, event):
        if not self.regions_data: 
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self.polygons_cache = []

        min_lon, max_lon, min_lat, max_lat = 13.3, 16.6, 45.4, 47.0
        
        geo_width = max_lon - min_lon
        geo_height = max_lat - min_lat
        geo_ratio = geo_width / geo_height * 0.7

        margin = 20
        canvas_w = self.width() - 2 * margin
        canvas_h = self.height() - 2 * margin
        canvas_ratio = canvas_w / canvas_h

        if canvas_ratio > geo_ratio:
            map_h = canvas_h
            map_w = map_h * geo_ratio
        else:
            map_w = canvas_w
            map_h = map_w / geo_ratio

        center_x = margin + (canvas_w - map_w) / 2
        center_y = margin + (canvas_h - map_h) / 2

        def scale(lon, lat):
            x = center_x + ((lon - min_lon) / geo_width) * map_w
            y = center_y + (1.0 - (lat - min_lat) / geo_height) * map_h
            
            x = (x - self.width() / 2) * self.zoom_factor + self.width() / 2 + self.pan_offset.x()
            y = (y - self.height() / 2) * self.zoom_factor + self.height() / 2 + self.pan_offset.y()
            return QPointF(x, y)

        for feature in self.regions_data:
            name = feature['properties'].get('NAME_LATN', '') 
            color = QColor(255, 100, 0, 200) if name in self.highlighted else QColor(100, 150, 255, 150)
            
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(Qt.black, 1))

            geom = feature['geometry']
            coords = geom['coordinates'] if geom['type'] == 'Polygon' else [r for p in geom['coordinates'] for r in p]
            
            for ring in coords:
                poly = QPolygonF([scale(p[0], p[1]) for p in ring])
                painter.drawPolygon(poly)
                self.polygons_cache.append((poly, name))
    
    def load_nuts3_data(self):
        file_path = os.path.join(os.path.dirname(__file__), "..", "final_data", "NUTS_RG_60M_2024_4326_LEVL_3.geojson")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.regions_data = [f for f in data['features'] if f['properties']['NUTS_ID'].startswith('SI')]
        except Exception as e:
            print(f"Error loading Map: {e}")