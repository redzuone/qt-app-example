import polars as pl
from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QTableWidget, QTableWidgetItem

from app.constants.data_schema import SCHEMA


class TableView(QTableWidget):
    delete_target_by_id = Signal(str)
    view_target_on_map = Signal(str)
    
    COLUMN_LABELS = {
        SCHEMA.DATETIME: 'Date/Time',
        SCHEMA.TYPE: 'Type',
        SCHEMA.TARGET_ID: 'Target ID',
        SCHEMA.TARGET_NAME: 'Target Name',
        SCHEMA.LATITUDE: 'Latitude',
        SCHEMA.LONGITUDE: 'Longitude',
        SCHEMA.HEIGHT: 'Height (m)',
        SCHEMA.SPEED: 'Speed (m/s)',
    }

    def __init__(self, rows: int = 0, columns: int = 8) -> None:
        super().__init__(rows, columns)
        header = self.horizontalHeader()
        header.setSectionsMovable(True)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        self.setHorizontalHeaderLabels([value for _, value in self.COLUMN_LABELS.items()])

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # NOTE: Enable sorting after populating
        # self.setSortingEnabled(True)

    def update_table(self, df: pl.DataFrame) -> None:
        '''Update table with new data from DataFrame'''
        df = df.sort('datetime', descending=False)
        self.setRowCount(len(df))
        self.setColumnCount(len(df.columns))
        self.setHorizontalHeaderLabels([self.COLUMN_LABELS.get(col, col) for col in df.columns])

        latitude_idx = df.columns.index(SCHEMA.LATITUDE)
        longitude_idx = df.columns.index(SCHEMA.LONGITUDE)
        
        for row_idx, row in enumerate(df.iter_rows()):
            for col_idx, value in enumerate(row):
                if value is None:
                    value = ''
                elif col_idx == latitude_idx or col_idx == longitude_idx:
                    value = f'{value:.6f}'
                item = QTableWidgetItem(str(value))
                self.setItem(row_idx, col_idx, item)

    def _get_column_index(self, schema_key: str) -> int | None:
        '''Find column index by schema key, returns None if not found'''
        target_label = self.COLUMN_LABELS.get(schema_key)
        if target_label is None:
            return None

        for col in range(self.columnCount()):
            header_item = self.horizontalHeaderItem(col)
            if header_item and header_item.text() == target_label:
                return col
        return None

    def _show_context_menu(self, position: QPoint) -> None:
        '''Show context menu for right-click on row'''
        if not self.selectedItems():
            return

        menu = QMenu(self)
        view_map_action = QAction('View on Map', self)
        view_map_action.triggered.connect(self._on_view_on_map)
        menu.addAction(view_map_action)
        
        delete_action = QAction('Delete Target', self)
        delete_action.triggered.connect(self._on_delete_target)
        menu.addAction(delete_action)
        
        # Show menu at cursor position
        menu.exec(self.viewport().mapToGlobal(position))

    def _on_view_on_map(self) -> None:
        '''Handle view on map action'''
        current_row = self.currentRow()
        if current_row < 0:
            return
        
        target_id_col = self._get_column_index(SCHEMA.TARGET_ID)
        if target_id_col is None:
            return
        
        target_id_item = self.item(current_row, target_id_col)
        if target_id_item:
            target_id = target_id_item.text()
            self.view_target_on_map.emit(target_id)
    
    def _on_delete_target(self) -> None:
        '''Handle delete target action'''
        current_row = self.currentRow()
        if current_row < 0:
            return
        
        target_id_col = self._get_column_index(SCHEMA.TARGET_ID)
        if target_id_col is None:
            return
        
        target_id_item = self.item(current_row, target_id_col)
        if target_id_item:
            target_id = target_id_item.text()
            self.delete_target_by_id.emit(target_id)
