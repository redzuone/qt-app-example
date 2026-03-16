import math
import random
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
	heading_deg: float = 0.0
	speed_mps: float = 0.0
	turn_rate_deg_s: float = 0.0
	phased_offset: float = 0.0
	tick: int = 0


class SimulatorService(QObject):
	new_raw_data = Signal(dict)
	simulation_started = Signal(int)
	simulation_stopped = Signal(int)

	def __init__(self, interval_ms: int = 1000) -> None:
		super().__init__()
		self._targets: dict[int, _TargetState] = {}
		self._interval_seconds = max(interval_ms, 1) / 1000.0
		self._timer = QTimer(self)
		self._timer.setInterval(interval_ms)
		self._timer.timeout.connect(self._emit_for_targets)

	@Slot(dict)
	def start_simulation(self, target_data: dict[str, Any]) -> None:
		target_id = int(target_data['target_id'])
		target_type = str(target_data.get('type', 'raw_data'))
		static = bool(target_data.get('static', True))

		rng = random.Random(target_id)
		heading_deg = rng.uniform(0.0, 360.0)
		if static:
			speed_mps = 0.0
			turn_rate_deg_s = 0.0
		else:
			if target_type == 'vehicle':
				speed_mps = rng.uniform(10.0, 38.0)
				turn_rate_deg_s = rng.uniform(-3.0, 3.0)
			elif target_type == 'target':
				speed_mps = rng.uniform(4.0, 20.0)
				turn_rate_deg_s = rng.uniform(-5.0, 5.0)
			else:
				speed_mps = rng.uniform(2.0, 10.0)
				turn_rate_deg_s = rng.uniform(-2.0, 2.0)

		target_state = _TargetState(
			target_id=target_id,
			target_name=str(target_data.get('target_name', f'Target {target_id}')).strip()
			or f'Target {target_id}',
			latitude=float(target_data['latitude']),
			longitude=float(target_data['longitude']),
			static=static,
			target_type=target_type,
			heading_deg=heading_deg,
			speed_mps=speed_mps,
			turn_rate_deg_s=turn_rate_deg_s,
			phased_offset=rng.uniform(0.0, 2.0 * math.pi),
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
				time_step = self._interval_seconds
				turn_noise = math.sin(
					target_state.tick / 6.0 + target_state.phased_offset
				) * 0.8
				target_state.heading_deg = (
					target_state.heading_deg
					+ (target_state.turn_rate_deg_s + turn_noise) * time_step
				) % 360.0

				speed_variation = 1.0 + math.sin(
					target_state.tick / 9.0 + target_state.phased_offset
				) * 0.15
				distance_m = target_state.speed_mps * max(speed_variation, 0.2) * time_step
				heading_rad = math.radians(target_state.heading_deg)
				north_m = math.cos(heading_rad) * distance_m
				east_m = math.sin(heading_rad) * distance_m

				lat_rad = math.radians(target_state.latitude)
				meters_per_deg_lat = 111_320.0
				meters_per_deg_lon = max(111_320.0 * abs(math.cos(lat_rad)), 1.0)
				target_state.latitude += north_m / meters_per_deg_lat
				target_state.longitude += east_m / meters_per_deg_lon

				if target_state.latitude > 89.9:
					target_state.latitude = 89.9
					target_state.heading_deg = (180.0 - target_state.heading_deg) % 360.0
				elif target_state.latitude < -89.9:
					target_state.latitude = -89.9
					target_state.heading_deg = (180.0 - target_state.heading_deg) % 360.0

				target_state.longitude = (
					(target_state.longitude + 180.0) % 360.0
				) - 180.0

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
