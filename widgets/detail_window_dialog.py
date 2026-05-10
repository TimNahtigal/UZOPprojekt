import html
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QTableWidgetItem, QTableWidget
import re

class NewsDetailWindow(QDialog):
    def __init__(self, title, content, word_importances, parent=None):
        super().__init__(parent)
        self.setWindowTitle("News Detail")
        self.resize(600, 500)
        
        layout = QVBoxLayout(self)

        title_label = QLabel(f"<h2>{title}</h2>")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        legend = QLabel("""
        <table style="
            border-collapse: collapse;
            border: 1px solid #bdbdbd;
            font-size: 12px;
            margin-bottom: 8px;
            background: transparent;
        ">
            <tr style="background:#efefef;">
                <th style="padding:6px 10px; border:1px solid #ccc;">Intenziteta</th>
                <th style="padding:6px 10px; border:1px solid #ccc;">Pomen</th>
            </tr>

            <tr>
                <td style="background: rgba(255,193,7,0.25); padding:6px 10px; border:1px solid #ccc; font-weight: bold;">
                    Nizka
                </td>
                <td style="padding:6px 10px; border:1px solid #ccc;">
                    Manj pomembne besede v gruči/članku
                </td>
            </tr>

            <tr>
                <td style="background: rgba(255,193,7,1.0); padding:6px 10px; border:1px solid #ccc; font-weight: bold;">
                    Visoka
                </td>
                <td style="padding:6px 10px; border:1px solid #ccc;">
                    Najpomembnejše besede v gruči/članku
                </td>
            </tr>
        </table>
        """)
        layout.addWidget(legend)

        self.text_display = QTextEdit()
        self.text_display.setStyleSheet("""
        QTextEdit {color: #222222;font-size: 14px;
        line-height: 1.4;}""")

        self.text_display.setReadOnly(True)
        layout.addWidget(self.text_display)

        highlighted_html = self.apply_highlighting(content, word_importances)
        self.text_display.setHtml(highlighted_html)

    def apply_highlighting(self, content, word_importances):
        content = html.escape(str(content)) #ker je breakalo newline

        if not word_importances:
              return content.replace("\n", "<br><br>")
        max_importance = max((imp for _, imp in word_importances), default=0) #normalizacija
        if max_importance == 0:
            return content.replace("\n", "<br><br>")

        importance_map = {word.lower(): imp/max_importance for word, imp in word_importances if word}
        
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
                normalized = importance_map.get(clean_word, 0)

                if normalized > 0:
                    alpha = 0.20 + 0.80 * normalized
                    color = f"rgba(255, 193, 7, {alpha:.2f})"
                    html_parts.append(
                        f'<span style="background-color: {color};">{word}</span>'
                    )
                else:
                    html_parts.append(word)
            final_paragraphs.append(" ".join(html_parts))
        return "<br><br>".join(final_paragraphs)