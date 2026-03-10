import polars as pl
from PySide6.QtCore import Signal
from PySide6.QtGui import QAction, QCloseEvent, Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.views.map_view import MapView
from app.views.simulator_view import SimulatorView
from app.views.table_view import TableView
from app.views.tree_view import TreeView
from app.views.toolbar import ToolBar


class MainWindow(QMainWindow):
    """Main application window."""
    debug_action = Signal(str)

    def __init__(self, map_url: str) -> None:
        super().__init__()
        self.setWindowTitle('Qt Example')
        self.setMinimumSize(800, 600)
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self._aux_windows: list[QWidget] = []

        self._create_menu_bar()
        self._create_status_bar()
        self._create_tool_bar()

        self.table_view = TableView()
        self.map_view = MapView(map_url=map_url)
        self.tree_view = TreeView()
        self.simulator_view = SimulatorView()
        self.register_aux_window(self.simulator_view)

        splitter = QSplitter()
        left_splitter = QSplitter(Qt.Orientation.Vertical)

        left_splitter.addWidget(self.tree_view)
        left_splitter.addWidget(self.table_view)
        self.table_view.hide()
        splitter.addWidget(left_splitter)
        splitter.addWidget(self.map_view)
        splitter.setSizes([500, 500])
        layout.addWidget(splitter)

    def _create_menu_bar(self) -> None:
        self.menu_bar = self.menuBar()

        file_menu = self.menu_bar.addMenu('File')
        file_menu.addAction('Exit', self.close)

        view_menu = self.menu_bar.addMenu('View')
        view_menu.addAction('Table', lambda: self._toggle_visibility(self.table_view))
        view_menu.addAction('Tree', lambda: self._toggle_visibility(self.tree_view))

        debug_menu = self.menu_bar.addMenu('Debug')
        self.simulator_action = QAction('Show Simulator', self)
        self.simulator_action.triggered.connect(lambda: self._show_view(self.simulator_view))

        debug_menu.addAction(self.simulator_action)

        map_submenu = debug_menu.addMenu('Map')
        map_submenu.addAction('Leaflet map', lambda: self.debug_action.emit('show_leaflet_map'))
        map_submenu.addAction('Maplibre map', lambda: self.debug_action.emit('show_maplibre_map'))

    def _show_view(self, view: QWidget) -> None:
        view.showNormal()
        view.raise_()
        view.activateWindow()

    def _toggle_visibility(self, view: QWidget) -> None:
        if view.isVisible():
            view.hide()
        else:
            self._show_view(view)

    def register_aux_window(self, window: QWidget) -> None:
        if window not in self._aux_windows:
            self._aux_windows.append(window)

    def closeEvent(self, event: QCloseEvent) -> None:
        for window in self._aux_windows:
            if window.isVisible():
                window.close()
        super().closeEvent(event)

    def _create_status_bar(self) -> None:
        self.status_bar = self.statusBar()

    def _create_tool_bar(self) -> None:
        self.tool_bar = ToolBar()
        self.addToolBar(self.tool_bar)

    def update_table(self, df: pl.DataFrame) -> None:
        self.table_view.update_table(df)

    def set_map_url(self, url: str) -> None:
        self.map_view.set_map_url(url)
