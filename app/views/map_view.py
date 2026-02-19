from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class MapView(QWidget):

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        label = QLabel('MAP')
        label.setStyleSheet('font-size: 24px; font-weight: bold;')
        label.setMinimumSize(200, 200)

        layout.addWidget(label)
