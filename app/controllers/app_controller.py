import logging
from typing import Any

from app.models.app_model import AppModel
from app.services.simulator_service import SimulatorService
from app.views.main_window import MainWindow

logger = logging.getLogger(__name__)


class AppController:
    def __init__(
        self,
        model: AppModel,
        view: MainWindow,
        simulator_service: SimulatorService | None = None,
    ):
        self._model = model
        self._view = view
        self._simulator_service = simulator_service

        if self._simulator_service is not None:
            self._connect_simulator()

    def _connect_simulator(self) -> None:
        simulator_service = self._simulator_service
        if simulator_service is None:
            return

        simulator_view = self._view.simulator_view
        simulator_view.start_simulation_requested.connect(
            simulator_service.start_simulation
        )
        simulator_view.stop_simulation_requested.connect(
            simulator_service.stop_simulation
        )

        simulator_service.simulation_started.connect(
            lambda target_id: simulator_view.set_target_running(target_id, True)
        )
        simulator_service.simulation_stopped.connect(
            lambda target_id: simulator_view.set_target_running(target_id, False)
        )
        simulator_service.new_raw_data.connect(self._handle_raw_data)

    def _handle_raw_data(self, payload: dict[str, Any]) -> None:
        logger.info('simulator raw data: %s', payload)
