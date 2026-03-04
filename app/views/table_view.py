import polars as pl
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

from app.constants.data_schema import SCHEMA


class TableView(QTableWidget):
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
