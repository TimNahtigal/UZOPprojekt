import html
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit

class NewsDetailWindow(QDialog):
    def __init__(self, title, content, word_importances, parent=None):
        super().__init__(parent)
        self.setWindowTitle("News Detail")
        self.resize(600, 500)
        
        layout = QVBoxLayout(self)

        title_label = QLabel(f"<h2>{title}</h2>")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        layout.addWidget(self.text_display)

        highlighted_html = self.apply_highlighting(content, word_importances)
        self.text_display.setHtml(highlighted_html)

    def apply_highlighting(self, content, word_importances):
        if not word_importances:
            return content

        importance_map = {word.lower(): imp for word, imp in word_importances if word}
        
        words = content.split(' ')
        html_parts = []

        for word in words:
            clean_word = word.strip(".,!?:;()\"'").lower()
            importance = importance_map.get(clean_word, 0)

            if importance and importance > 0:
                alpha = min(int(importance * 255 * 5), 255)
                color = f"rgba(255, 255, 0, {alpha/255:.2f})"
                html_parts.append(f'<span style="background-color: {color};">{word}</span>')
            else:
                html_parts.append(word)

        return " ".join(html_parts)