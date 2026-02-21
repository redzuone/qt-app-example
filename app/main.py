import logging
import sys

import qt_themes
from PySide6.QtWidgets import QApplication

from app.controllers.app_controller import AppController
from app.models.app_model import AppModel
from app.services.map_service import MapService
from app.views.main_window import MainWindow


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    )

    app = QApplication(sys.argv)
    qt_themes.set_theme('nord')
    map_service = MapService()
    map_service.start()
    app.aboutToQuit.connect(map_service.stop)

    model = AppModel()
    view = MainWindow(map_url=map_service.map_url)
    controller = AppController(model=model, view=view)
    view.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
