import multiprocessing as mp
import os
import sys

import qt_themes  # type: ignore[import-untyped]
from PySide6.QtWidgets import QApplication

from app.constants import APP_DISPLAY_NAME
from app.controllers.app_controller import AppController
from app.models.app_model import AppModel
from app.services.data_store import DataStore
from app.services.map_service import MapService
from app.services.simulator_service import SimulatorService
from app.utils.app_settings import create_app_settings
from app.utils.logging_config import configure_logging
from app.utils.windows_title_bar import apply_windows_dark_style
from app.views.main_window import MainWindow


def main() -> None:
    # Fix Uvicorn logging when frozen without a console
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w')
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w')

    configure_logging()

    app = QApplication(sys.argv)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    qt_themes.set_theme('one_dark_two')
    settings = create_app_settings()
    map_service = MapService()
    map_service.start()
    app.aboutToQuit.connect(map_service.stop)

    simulator_service = SimulatorService()
    app.aboutToQuit.connect(simulator_service.stop_all)

    model = AppModel()
    view = MainWindow(map_url=map_service.map_url, settings=settings)
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
    mp.freeze_support()
    main()
