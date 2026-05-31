import html
from collections import defaultdict
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QToolTip
from PySide6.QtGui import QMouseEvent, QTextCursor
from PySide6.QtCore import Qt

class NewsDetailWindow(QDialog):
    def __init__(self, title, content, word_importances, intersected_naselja, parent=None):
        super().__init__(parent)
        self.setWindowTitle("News Detail")
        self.resize(600, 600) # Slightly increased height for the extra header area
        
        layout = QVBoxLayout(self)

        # 1. News Title
        title_label = QLabel(f"<h2>{title}</h2>")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        # 2. Dynamic Regions and Settlements Label
        if intersected_naselja:
            region_groups = defaultdict(list)
            for r_id, r_name, naselje in intersected_naselja:
                if naselje not in region_groups[r_name]:
                    region_groups[r_name].append(naselje)

            # Build HTML representation
            geo_html = """
            <div style="padding: 8px 12px; font-size: 13px; color: #333;"><strong>Regije, kamor članek sodi:</strong>
            """
            for r_name, settlements in region_groups.items():
                settlements_str = ", ".join(settlements)
                geo_html += f'<div style="margin-top: 2px;">• <strong>{r_name}</strong>: {settlements_str}</div>'
            geo_html += "</div>"

            geo_label = QLabel(geo_html)
            geo_label.setWordWrap(True)
            layout.addWidget(geo_label)

        # 3. Text Cluster Importance Legend
        legend = QLabel("""
        <div style="font-size: 12px; color: #555; margin-bottom: 8px;">
            Označene besede so ključne za to gručo — 
            <span style="background: rgba(255,193,7,0.3); padding: 1px 4px;">manj pomembne</span> 
            do 
            <span style="background: rgba(255,193,7,1.0); padding: 1px 4px;">najpomembnejše</span>
        </div>
        """)
        layout.addWidget(legend)

        # 4. Content Main Viewport Display
        self.text_display = QTextEdit()
        self.text_display.setStyleSheet("""
        QTextEdit {
            color: #222222;
            font-size: 14px;
            line-height: 1.4;
        }""")
        self.text_display.setReadOnly(True)
        
        self.text_display.setMouseTracking(True)
        self.text_display.viewport().setMouseTracking(True)
        self.text_display.viewport().installEventFilter(self)

        layout.addWidget(self.text_display)

        highlighted_html = self.apply_highlighting(content, word_importances)
        self.text_display.setHtml(highlighted_html)

    def eventFilter(self, obj, event):
        if obj == self.text_display.viewport() and isinstance(event, QMouseEvent):
            pos = event.position().toPoint()
            anchor = self.text_display.anchorAt(pos)
            
            if anchor.startswith("importance:"):
                percentage = anchor.split(":")[1]
                QToolTip.showText(event.globalPosition().toPoint(), f"Importance: {percentage}", self.text_display)
            else:
                QToolTip.hideText()
                
        return super().eventFilter(obj, event)

    def apply_highlighting(self, content, word_importances):
        content = html.escape(str(content))

        if not word_importances:
            return content.replace("\n", "<br><br>")
        
        max_importance = max((imp for _, imp in word_importances), default=0)
        if max_importance == 0:
            return content.replace("\n", "<br><br>")

        importance_map = {}
        for word, imp in word_importances:
            if word:
                clean_w = word.lower()
                importance_map[clean_w] = {
                    'normalized': imp / max_importance,
                    'original': imp
                }
        
        paragraphs = content.split("\n")
        final_paragraphs = []
        for paragraph in paragraphs:
            words = paragraph.split(" ")
            html_parts = []

            for word in words:
                clean_word = "".join(
                    c.lower() for c in word
                    if c.isalpha() or c in "čšžćđ-"
                )
                
                word_data = importance_map.get(clean_word)

                if word_data and word_data['normalized'] > 0:
                    normalized = word_data['normalized']
                    original_val = word_data['original']
                    
                    alpha = 0.20 + 0.80 * normalized
                    color = f"rgba(255, 193, 7, {alpha:.2f})"
                    
                    percentage_str = f"{original_val * 100:.1f}%"
                    
                    html_parts.append(
                        f'<a href="importance:{percentage_str}" style="text-decoration: none; color: inherit; background-color: {color};">{word}</a>'
                    )
                else:
                    html_parts.append(word)
            final_paragraphs.append(" ".join(html_parts))
        return "<br><br>".join(final_paragraphs)