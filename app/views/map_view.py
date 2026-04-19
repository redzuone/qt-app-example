from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QVBoxLayout, QWidget


class MapView(QWidget):
    def __init__(self, map_url: str) -> None:
        super().__init__()
        self.setMinimumSize(200, 200)

        layout = QVBoxLayout(self)
        self._web_view = QWebEngineView(self)
        self._web_view.setUrl(QUrl(map_url))
        layout.addWidget(self._web_view)

    def set_map_url(self, url: str) -> None:
        self._web_view.setUrl(QUrl(url))
