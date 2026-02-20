from PyQt6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from app.views.map_view import MapView
from app.views.table_view import TableView
from app.views.toolbar import ToolBar


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, map_url: str) -> None:
        super().__init__()
        self.setWindowTitle('PyQt Example')
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self._create_menu_bar()
        self._create_status_bar()
        self._create_tool_bar()

        self.table_view = TableView()
        self.map_view = MapView(map_url=map_url)

        content_layout = QHBoxLayout()

        content_layout.addWidget(self.table_view)
        content_layout.addWidget(self.map_view)
        layout.addLayout(content_layout)

    def _create_menu_bar(self) -> None:
        self.menu_bar = self.menuBar()
        assert self.menu_bar is not None

        file_menu = self.menu_bar.addMenu('File')
        assert file_menu is not None
        file_menu.addAction('Exit', self.close)

        debug_menu = self.menu_bar.addMenu('Debug')
        assert debug_menu is not None
        debug_menu.addAction('Test')

    def _create_status_bar(self) -> None:
        self.status_bar = self.statusBar()
        assert self.status_bar is not None

    def _create_tool_bar(self) -> None:
        self.tool_bar = ToolBar()
        self.addToolBar(self.tool_bar)
        assert self.tool_bar is not None
