import json
import os
import requests
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtGui import QPainter, QPen, QPolygonF, QColor, QBrush
from PySide6.QtCore import Qt, QPointF

class MapWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.regions = []
        self.load_nuts3_data()
        self.setMinimumSize(400, 400)

    def load_nuts3_data(self):
        file_path = os.path.join(os.path.dirname(__file__), "..\\final_data\\NUTS_RG_60M_2024_4326_LEVL_3.geojson")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.regions = [
                f for f in data['features'] 
                if f['properties']['NUTS_ID'].startswith('SI')
            ]

            if self.regions:
                self._calculate_bounds()
                
        except FileNotFoundError:
            print(f"Error: File not found at {file_path}")
        except Exception as e:
            print(f"Error loading local GeoJSON: {e}")

    def paintEvent(self, event):
        if not self.regions:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Simple coordinate scaling to fit Slovenia in the widget
        # Slovenia bounds approx: Lon 13.3 to 16.6, Lat 45.4 to 47.0
        min_lon, max_lon = 13.3, 16.6
        min_lat, max_lat = 45.4, 47.0
        
        def scale(lon, lat):
            x = (lon - min_lon) / (max_lon - min_lon) * self.width()
            y = (1.0 - (lat - min_lat) / (max_lat - min_lat)) * self.height()
            return QPointF(x, y)

        painter.setPen(QPen(Qt.black, 1))
        painter.setBrush(QBrush(QColor(100, 150, 255, 150)))

        for feature in self.regions:
            geom = feature['geometry']
            if geom['type'] == 'Polygon':
                for ring in geom['coordinates']:
                    poly = QPolygonF([scale(p[0], p[1]) for p in ring])
                    painter.drawPolygon(poly)
            elif geom['type'] == 'MultiPolygon':
                for polygon in geom['coordinates']:
                    for ring in polygon:
                        poly = QPolygonF([scale(p[0], p[1]) for p in ring])
                        painter.drawPolygon(poly)
