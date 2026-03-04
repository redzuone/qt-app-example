import logging
import sys

import qt_themes  # type: ignore[import-untyped]
from PySide6.QtWidgets import QApplication

from app.controllers.app_controller import AppController
from app.models.app_model import AppModel
from app.services.data_store import DataStore
from app.services.map_service import MapService
from app.services.simulator_service import SimulatorService
from app.utils.windows_title_bar import apply_windows_dark_style
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

    simulator_service = SimulatorService()
    app.aboutToQuit.connect(simulator_service.stop_all)

    model = AppModel()
    view = MainWindow(map_url=map_service.map_url)
    data_store = DataStore()
    apply_windows_dark_style(view)
    _controller = AppController(
        data_store=data_store,
        model=model,
        view=view,
        map_service=map_service,
        simulator_service=simulator_service,
    )
    view.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
