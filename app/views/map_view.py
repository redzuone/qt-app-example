from PyQt6.QtCore import QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QVBoxLayout, QWidget


class MapView(QWidget):

    def __init__(self, map_url: str) -> None:
        super().__init__()
        self.setMinimumSize(300, 300)

        layout = QVBoxLayout(self)
        self._web_view = QWebEngineView(self)
        self._web_view.setUrl(QUrl(map_url))
        layout.addWidget(self._web_view)
