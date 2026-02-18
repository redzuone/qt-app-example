import sys

from PyQt6.QtWidgets import QApplication

from app.controllers.app_controller import AppController
from app.models.app_model import AppModel
from app.views.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    model = AppModel()
    view = MainWindow()
    controller = AppController(model=model, view=view)
    view.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
