from PySide6.QtCore import Signal, QPointF, Qt
from PySide6.QtGui import QPainter, QPolygonF, QColor, QBrush, QPen
from PySide6.QtWidgets import QWidget
import json
import os

class MapWidget(QWidget):
    region_selected = Signal(list)

    def __init__(self):
        super().__init__()
        self.regions = []
        self.selected_regions = set()
        self.polygons_cache = []
        self.load_nuts3_data()
        self.setMinimumSize(400, 400)
    
    def mousePressEvent(self, event):
        click_pos = event.position()
        for poly, name in reversed(self.polygons_cache):
            if poly.containsPoint(click_pos, Qt.OddEvenFill):
                if name in self.selected_regions:
                    self.selected_regions.remove(name)
                else:
                    self.selected_regions.add(name)
                
                self.region_selected.emit(list(self.selected_regions))
                self.update()
                return

    def paintEvent(self, event):
        if not self.regions: return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self.polygons_cache = []

        min_lon, max_lon, min_lat, max_lat = 13.3, 16.6, 45.4, 47.0
        
        def scale(lon, lat):
            margin = 20
            x = margin + (lon - min_lon) / (max_lon - min_lon) * (self.width() - 2 * margin)
            y = (self.height() - margin) - (lat - min_lat) / (max_lat - min_lat) * (self.height() - 2 * margin)
            return QPointF(x, y)

        for feature in self.regions:
            name = feature['properties'].get('NAME_LATN', '') 
            
            # Highlight if name is in the set
            if name in self.selected_regions:
                painter.setBrush(QBrush(QColor(255, 100, 0, 200))) 
            else:
                painter.setBrush(QBrush(QColor(100, 150, 255, 150)))
            
            painter.setPen(QPen(Qt.black, 1))

            geom = feature['geometry']
            coords = geom['coordinates'] if geom['type'] == 'Polygon' else [r for p in geom['coordinates'] for r in p]
            
            for ring in coords:
                poly = QPolygonF([scale(p[0], p[1]) for p in ring])
                painter.drawPolygon(poly)
                self.polygons_cache.append((poly, name))
    
    def load_nuts3_data(self):
        # Using double backslashes for Windows paths or a raw string is good practice
        file_path = os.path.join(os.path.dirname(__file__), "..", "final_data", "NUTS_RG_60M_2024_4326_LEVL_3.geojson")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.regions = [
                f for f in data['features'] 
                if f['properties']['NUTS_ID'].startswith('SI')
            ]

            # REMOVED the call to _calculate_bounds to stop the error
            # or you can define it as shown above.
                
        except FileNotFoundError:
            print(f"Error: File not found at {file_path}")
        except Exception as e:
            print(f"Error loading local GeoJSON: {e}")