import polars as pl
from PySide6.QtCore import QByteArray, QSettings, QSize, Signal
from PySide6.QtGui import QAction, QCloseEvent, Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.constants import APP_DISPLAY_NAME
from app.views.map_view import MapView
from app.views.simulator_view import SimulatorView
from app.views.spectrum_view import SpectrumView
from app.views.table_view import TableView
from app.views.tree_view import TreeView
from app.views.toolbar import ToolBar
from app.views.waterfall_view import WaterfallView


class MainWindow(QMainWindow):
    """Main application window."""
    debug_action = Signal(str)
    settings_requested = Signal()
    trail_full_trail_toggled = Signal(bool)
    clear_all_trail_locks_requested = Signal()
    map_target_labels_toggled = Signal(bool)

    def __init__(self, map_url: str, settings: QSettings) -> None:
        super().__init__()
        self._settings = settings
        self.setWindowTitle(APP_DISPLAY_NAME)
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
        self.simulator_view = SimulatorView(settings=self._settings)
        self.register_aux_window(self.simulator_view)

        self.spectrum_view = SpectrumView()
        self.waterfall_view = WaterfallView()
        self.register_aux_window(self.spectrum_view)
        self.register_aux_window(self.waterfall_view)

        self._main_splitter = QSplitter()
        self._left_splitter = QSplitter(Qt.Orientation.Vertical)

        self._left_splitter.addWidget(self.tree_view)
        self._left_splitter.addWidget(self.table_view)
        self.table_view.hide()
        self._main_splitter.addWidget(self._left_splitter)
        self._main_splitter.addWidget(self.map_view)
        self._main_splitter.setSizes([500, 500])
        layout.addWidget(self._main_splitter)

        self._restore_window_settings()

    def _create_menu_bar(self) -> None:
        self.menu_bar = self.menuBar()

        file_menu = self.menu_bar.addMenu('File')
        preferences_menu = file_menu.addMenu('Preferences')
        preferences_menu.addAction('Settings', self.settings_requested.emit)
        file_menu.addAction('Exit', self.close)

        view_menu = self.menu_bar.addMenu('View')
        view_menu.addAction('Table', lambda: self._toggle_visibility(self.table_view))
        view_menu.addAction('Tree', lambda: self._toggle_visibility(self.tree_view))
        view_menu.addAction('Spectrum', lambda: self._toggle_visibility(self.spectrum_view))
        view_menu.addAction('Waterfall', lambda: self._toggle_visibility(self.waterfall_view))
        map_submenu = view_menu.addMenu('Map')

        self._target_labels_action = QAction('Target Labels', self)
        self._target_labels_action.setCheckable(True)
        self._target_labels_action.setChecked(False)
        self._target_labels_action.toggled.connect(self.map_target_labels_toggled.emit)
        map_submenu.addAction(self._target_labels_action)

        trails_submenu = map_submenu.addMenu('Trails')
        self._full_trail_action = QAction('Full Trail', self)
        self._full_trail_action.setCheckable(True)
        self._full_trail_action.setChecked(False)
        self._full_trail_action.toggled.connect(self.trail_full_trail_toggled.emit)
        trails_submenu.addAction(self._full_trail_action)

        clear_trail_locks_action = QAction('Clear All Trail Locks', self)
        clear_trail_locks_action.triggered.connect(
            self.clear_all_trail_locks_requested.emit
        )
        trails_submenu.addAction(clear_trail_locks_action)

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
        self._save_window_settings()
        for window in self._aux_windows:
            if window.isVisible():
                window.close()
        super().closeEvent(event)

    def _save_window_settings(self) -> None:
        if not self.isMaximized():
            self._settings.setValue('main_window/size', self.size())

        self._settings.setValue('main_window/is_maximized', self.isMaximized())
        self._settings.setValue('main_window/main_splitter_state', self._main_splitter.saveState())
        self._settings.setValue('main_window/left_splitter_state', self._left_splitter.saveState())
        self._settings.sync()

    def _restore_window_settings(self) -> None:
        saved_size = self._settings.value('main_window/size', type=QSize)
        if isinstance(saved_size, QSize) and saved_size.isValid():
            self.resize(saved_size)

        is_maximized = self._settings.value('main_window/is_maximized', False, type=bool)
        if is_maximized:
            self.showMaximized()

        main_splitter_state = self._settings.value(
            'main_window/main_splitter_state',
            type=QByteArray,
        )
        if isinstance(main_splitter_state, QByteArray) and not main_splitter_state.isEmpty():
            self._main_splitter.restoreState(main_splitter_state)

        left_splitter_state = self._settings.value(
            'main_window/left_splitter_state',
            type=QByteArray,
        )
        if isinstance(left_splitter_state, QByteArray) and not left_splitter_state.isEmpty():
            self._left_splitter.restoreState(left_splitter_state)

    def _create_status_bar(self) -> None:
        self.status_bar = self.statusBar()

    def _create_tool_bar(self) -> None:
        self.tool_bar = ToolBar()
        self.addToolBar(self.tool_bar)

    def update_table(self, df: pl.DataFrame) -> None:
        self.table_view.update_table(df)

    def set_map_url(self, url: str) -> None:
        self.map_view.set_map_url(url)
