from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem


class TableView(QTableWidget):
    def __init__(self, rows: int = 5, columns: int = 3) -> None:
        super().__init__(rows, columns)
        header = self.horizontalHeader()
        assert header is not None
        header.setSectionsMovable(True)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)

        for row in range(rows):
            for column in range(columns):
                item = QTableWidgetItem(f'Item {row + 1}, {column + 1}')
                self.setItem(row, column, item)

        # NOTE: Enable sorting after populating
        self.setSortingEnabled(True)
