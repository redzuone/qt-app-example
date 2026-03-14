import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from app.constants.data_schema import SCHEMA


@dataclass
class _TargetState:
	target_id: int
	target_name: str
	latitude: float
	longitude: float
	static: bool
	target_type: str
	tick: int = 0


class SimulatorService(QObject):
	new_raw_data = Signal(dict)
	simulation_started = Signal(int)
	simulation_stopped = Signal(int)

	def __init__(self, interval_ms: int = 1000) -> None:
		super().__init__()
		self._targets: dict[int, _TargetState] = {}
		self._timer = QTimer(self)
		self._timer.setInterval(interval_ms)
		self._timer.timeout.connect(self._emit_for_targets)

	@Slot(dict)
	def start_simulation(self, target_data: dict[str, Any]) -> None:
		target_id = int(target_data['target_id'])
		target_state = _TargetState(
			target_id=target_id,
			target_name=str(target_data.get('target_name', f'Target {target_id}')).strip()
			or f'Target {target_id}',
			latitude=float(target_data['latitude']),
			longitude=float(target_data['longitude']),
			static=bool(target_data.get('static', True)),
			target_type=str(target_data.get('type', 'raw_data')),
		)

		self._targets[target_id] = target_state
		if not self._timer.isActive():
			self._timer.start()

		self.simulation_started.emit(target_id)

	@Slot(int)
	def stop_simulation(self, target_id: int) -> None:
		removed = self._targets.pop(int(target_id), None)
		if removed is None:
			return

		self.simulation_stopped.emit(int(target_id))
		if not self._targets and self._timer.isActive():
			self._timer.stop()

	def stop_all(self) -> None:
		target_ids = list(self._targets.keys())
		for target_id in target_ids:
			self.stop_simulation(target_id)

	def _emit_for_targets(self) -> None:
		for target_state in self._targets.values():
			if not target_state.static:
				target_state.tick += 1
				base_increment = 0.0001
				lat_deviation = math.sin(target_state.tick / 3.0) * 0.00002
				lon_deviation = math.cos(target_state.tick / 4.0) * 0.00002
				target_state.latitude += base_increment + lat_deviation
				target_state.longitude += base_increment + lon_deviation

			self.new_raw_data.emit(
				{
					SCHEMA.TYPE: target_state.target_type,
					SCHEMA.TARGET_ID: target_state.target_id,
					SCHEMA.TARGET_NAME: target_state.target_name,
					SCHEMA.LATITUDE: target_state.latitude,
					SCHEMA.LONGITUDE: target_state.longitude,
					SCHEMA.DATETIME: datetime.now(UTC).isoformat(),
				}
			)
