import logging
from typing import Any

from PySide6.QtCore import QSettings

from app.constants.data_schema import SCHEMA
from app.models.app_model import AppModel
from app.services.data_store import DataStore
from app.services.map_service import MapService
from app.services.simulator_service import SimulatorService
from app.utils.app_settings import AppSettings, load_settings, save_settings
from app.views.main_window import MainWindow
from app.views.settings_dialog import SettingsDialog

logger = logging.getLogger(__name__)


class AppController:
    def __init__(
        self,
        data_store: DataStore,
        model: AppModel,
        view: MainWindow,
        settings: QSettings,
        map_service: MapService | None = None,
        simulator_service: SimulatorService | None = None,
    ):
        self._data_store = data_store
        self._model = model
        self._view = view
        self._qs = settings
        self._app_settings: AppSettings = load_settings(settings)
        self._map_service = map_service
        self._simulator_service = simulator_service
        self._show_full_trails = False
        self._locked_trail_target_ids: set[str] = set()

        # Connect signals by feature groups, regardless of direction
        if self._simulator_service is not None:
            self._connect_simulator()
        if self._data_store is not None:
            self._connect_data_store()
        self._connect_table_view()
        self._connect_tree_view()
        self._connect_map()
        self._connect_misc_signals()

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
        simulator_view.stop_all_simulation_requested.connect(
            simulator_service.stop_all
        )

        simulator_service.simulation_started.connect(
            lambda target_id: simulator_view.set_target_running(target_id, True)
        )
        simulator_service.simulation_stopped.connect(
            lambda target_id: simulator_view.set_target_running(target_id, False)
        )
        simulator_service.new_raw_data.connect(self._handle_raw_data)

    def _connect_data_store(self) -> None:
        data_store = self._data_store
        data_store.data_updated.connect(self._handle_data_updated)

        self._view.table_view.delete_target_by_id.connect(
            self._data_store.delete_target
        )

    def _connect_table_view(self) -> None:
        '''Connect table view signals'''
        self._view.table_view.view_target_on_map.connect(self._on_view_target_on_map)

    def _connect_tree_view(self) -> None:
        '''Connect tree view signals'''
        tree_view = self._view.tree_view
        if tree_view is None:
            return
        tree_view.view_target_on_map.connect(self._on_view_target_on_map)
        tree_view.delete_target_by_id.connect(
            self._data_store.delete_target
        )
        tree_view.lock_trail_to_target.connect(self._on_lock_trail_to_target)
        tree_view.unlock_trail_from_target.connect(self._on_unlock_trail_from_target)
        tree_view.clear_all_trail_locks_requested.connect(self._on_clear_all_trail_locks)

    def _connect_map(self) -> None:
        if self._map_service is not None:
            self._map_service.set_web_message_handler(self._handle_map_web_message)

    def _connect_misc_signals(self) -> None:
        self._view.debug_action.connect(self._handle_debug_action)
        self._view.settings_requested.connect(self._open_settings_dialog)
        self._view.trail_full_trail_toggled.connect(self._on_trail_mode_toggled)
        self._view.clear_all_trail_locks_requested.connect(
            self._on_clear_all_trail_locks
        )

    def _on_view_target_on_map(self, target_id: str) -> None:
        '''Handle view target on map request'''
        if self._map_service is None or self._data_store is None:
            return

        latest_row = self._data_store.get_latest_for_target(target_id)
        if latest_row is None:
            logger.warning(f'No data found for target {target_id}')
            return
 
        latitude = latest_row.get(SCHEMA.LATITUDE)
        longitude = latest_row.get(SCHEMA.LONGITUDE)

        if latitude is None or longitude is None:
            logger.warning(f'Missing coordinates for target {target_id}')
            return

        self._map_service.focus_target(target_id, latitude, longitude)

    def _handle_raw_data(self, payload: dict[str, Any]) -> None:
        self._data_store.add_data(payload)

    def _handle_data_updated(self) -> None:
        '''Handle updates from data store'''
        latest_df = self._data_store.get_latest_per_target()
        self._view.update_table(latest_df)
        if self._view.tree_view is not None:
            self._view.tree_view.update_tree(latest_df)
        if self._map_service is not None:
            self._map_service.update_targets(latest_df)
            self._update_map_trails()

    def _update_map_trails(self) -> None:
        if self._map_service is None:
            return

        max_points_per_target = 0 if self._show_full_trails else 200
        trail_df = self._data_store.get_trail_points_per_target(
            max_points_per_target,
            self._locked_trail_target_ids or None,
        )
        self._map_service.update_trails(
            trail_df,
            not self._show_full_trails,
        )

    def _on_trail_mode_toggled(self, enabled: bool) -> None:
        self._show_full_trails = enabled
        self._update_map_trails()

    def _on_lock_trail_to_target(self, target_id: str) -> None:
        self._locked_trail_target_ids.add(target_id)
        self._update_map_trails()

    def _on_unlock_trail_from_target(self, target_id: str) -> None:
        if target_id not in self._locked_trail_target_ids:
            return
        self._locked_trail_target_ids.remove(target_id)
        self._update_map_trails()

    def _on_clear_all_trail_locks(self) -> None:
        if not self._locked_trail_target_ids:
            return
        self._locked_trail_target_ids.clear()
        self._update_map_trails()

    def _handle_debug_action(self, action_name: str) -> None:
        if self._map_service is None:
            return
        if action_name == 'show_leaflet_map':
            self._view.set_map_url(self._map_service.base_url + '/leaflet')
        elif action_name == 'show_maplibre_map':
            self._view.set_map_url(self._map_service.base_url + '/maplibre')

    def _open_settings_dialog(self) -> None:
        dialog = SettingsDialog(app_settings=self._app_settings, parent=self._view)
        if dialog.exec() == 0:
            return

        latitude, longitude = dialog.sensor_center()
        self._app_settings.sensor_latitude = latitude
        self._app_settings.sensor_longitude = longitude
        save_settings(self._qs, self._app_settings)

        if self._map_service is not None:
            self._map_service.set_sensor_center(latitude=latitude, longitude=longitude)

    def _handle_map_web_message(self, connection_id: int, message: dict[str, Any]) -> None:
        if self._map_service is None:
            return

        if message.get('type') != 'websocket_connected':
            return

        latitude = self._app_settings.sensor_latitude
        longitude = self._app_settings.sensor_longitude
        self._map_service.set_sensor_center(
            latitude=latitude,
            longitude=longitude,
            connection_id=connection_id,
        )
