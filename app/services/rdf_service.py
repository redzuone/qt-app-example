import math
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from PySide6.QtCore import QObject, QThread, Signal, Slot

from app.constants.data_schema import SCHEMA


@dataclass(frozen=True)
class RdfReport:
    station_id: int
    frequency_hz: float
    bearing_deg: float
    timestamp: datetime


@dataclass
class _TrackPoint:
    track_id: str
    frequency_hz: float
    latitude: float
    longitude: float
    updated_at: datetime


@dataclass
class _StationConfig:
    latitude: float
    longitude: float
    altitude_m: float
    bearing_offset_deg: float


class _RdfTrackIndex:
    """Simple in-memory proximity matcher for stable RDF fix IDs."""

    def __init__(self, max_age_seconds: int = 600, match_radius_m: float = 1_500.0) -> None:
        self._points: list[_TrackPoint] = []
        self._next_id = 1
        self._max_age = timedelta(seconds=max(max_age_seconds, 1))
        self._match_radius_m = max(match_radius_m, 10.0)

    def set_match_radius(self, match_radius_m: float) -> None:
        self._match_radius_m = max(match_radius_m, 10.0)

    def assign_track_id(
        self,
        *,
        frequency_hz: float,
        latitude: float,
        longitude: float,
        now: datetime,
    ) -> str:
        self._points = [point for point in self._points if now - point.updated_at <= self._max_age]

        best_point: _TrackPoint | None = None
        best_distance = float('inf')
        for point in self._points:
            if abs(point.frequency_hz - frequency_hz) > 1e-6:
                continue
            distance_m = _haversine_m(
                lat1=latitude,
                lon1=longitude,
                lat2=point.latitude,
                lon2=point.longitude,
            )
            if distance_m < best_distance:
                best_distance = distance_m
                best_point = point

        if best_point is not None and best_distance <= self._match_radius_m:
            best_point.latitude = latitude
            best_point.longitude = longitude
            best_point.updated_at = now
            return best_point.track_id

        track_id = f'RDF-{self._next_id:06d}'
        self._next_id += 1
        self._points.append(
            _TrackPoint(
                track_id=track_id,
                frequency_hz=frequency_hz,
                latitude=latitude,
                longitude=longitude,
                updated_at=now,
            )
        )
        return track_id


class RdfTriangulationWorker(QObject):
    triangulation_ready = Signal(dict)

    def __init__(self) -> None:
        super().__init__()
        self._track_index = _RdfTrackIndex()
        self._station_configs: dict[int, _StationConfig] = {
            1: _StationConfig(0.0, -0.01, 0.0, 0.0),
            2: _StationConfig(0.0, 0.01, 0.0, 0.0),
        }
        self._distance_tolerance_m = 1_500.0

    @Slot(float, float)
    def set_sensor_center(self, latitude: float, longitude: float) -> None:
        # Keep two stations offset from sensor center to produce intersections by default.
        self.configure_station(1, latitude, longitude - 0.01, 0.0, 0.0)
        self.configure_station(2, latitude, longitude + 0.01, 0.0, 0.0)

    @Slot(int, float, float, float, float)
    def configure_station(
        self,
        station_id: int,
        latitude: float,
        longitude: float,
        altitude_m: float,
        bearing_offset_deg: float,
    ) -> None:
        if station_id not in (1, 2):
            return
        self._station_configs[station_id] = _StationConfig(
            latitude=latitude,
            longitude=longitude,
            altitude_m=altitude_m,
            bearing_offset_deg=bearing_offset_deg,
        )

    @Slot(float)
    def set_distance_tolerance(self, distance_tolerance_m: float) -> None:
        self._distance_tolerance_m = max(distance_tolerance_m, 0.0)
        self._track_index.set_match_radius(self._distance_tolerance_m)

    @Slot(dict, dict)
    def triangulate(self, report_a: dict[str, float | int | str], report_b: dict[str, float | int | str]) -> None:
        triangulation = self._triangulate_reports(report_a=report_a, report_b=report_b)
        if triangulation is None:
            return

        fix_lat, fix_lon, crossing_error_m = triangulation
        timestamp = datetime.now(UTC)
        frequency_hz = float(report_a[SCHEMA.FREQUENCY])
        fix_id = self._track_index.assign_track_id(
            frequency_hz=frequency_hz,
            latitude=fix_lat,
            longitude=fix_lon,
            now=timestamp,
        )

        if crossing_error_m > self._distance_tolerance_m:
            return


        payload = {
            SCHEMA.TYPE: 'rdf_fix',
            SCHEMA.TARGET_ID: fix_id,
            SCHEMA.TARGET_NAME: f'RDF {frequency_hz:.3f} Hz',
            SCHEMA.LATITUDE: fix_lat,
            SCHEMA.LONGITUDE: fix_lon,
            SCHEMA.HEIGHT: None,
            SCHEMA.SPEED: crossing_error_m,
            SCHEMA.DATETIME: timestamp.isoformat(),
        }
        self.triangulation_ready.emit(payload)

    def _triangulate_reports(
        self, report_a: dict[str, float | int | str], report_b: dict[str, float | int | str]
    ) -> tuple[float, float, float] | None:
        station_a = int(report_a[SCHEMA.STATION_ID])
        station_b = int(report_b[SCHEMA.STATION_ID])
        if station_a == station_b:
            return None

        config_a = self._station_configs.get(station_a)
        config_b = self._station_configs.get(station_b)
        if config_a is None or config_b is None:
            return None

        lat_ref = (config_a.latitude + config_b.latitude) / 2.0
        meters_per_deg_lat = 111_320.0
        meters_per_deg_lon = max(111_320.0 * abs(math.cos(math.radians(lat_ref))), 1.0)

        p1x = 0.0
        p1y = 0.0
        p2x = (config_b.longitude - config_a.longitude) * meters_per_deg_lon
        p2y = (config_b.latitude - config_a.latitude) * meters_per_deg_lat

        b1_deg = (float(report_a[SCHEMA.BEARING]) + config_a.bearing_offset_deg) % 360.0
        b2_deg = (float(report_b[SCHEMA.BEARING]) + config_b.bearing_offset_deg) % 360.0
        b1 = math.radians(b1_deg)
        b2 = math.radians(b2_deg)
        d1x, d1y = math.sin(b1), math.cos(b1)
        d2x, d2y = math.sin(b2), math.cos(b2)

        cross = d1x * d2y - d1y * d2x
        if abs(cross) < 1e-5:
            return None

        dx = p2x - p1x
        dy = p2y - p1y
        t1 = (dx * d2y - dy * d2x) / cross
        t2 = (dx * d1y - dy * d1x) / cross

        if t1 < 0.0 or t2 < 0.0:
            return None

        i1x = p1x + d1x * t1
        i1y = p1y + d1y * t1
        i2x = p2x + d2x * t2
        i2y = p2y + d2y * t2

        fix_x = (i1x + i2x) / 2.0
        fix_y = (i1y + i2y) / 2.0
        crossing_error_m = math.hypot(i1x - i2x, i1y - i2y)

        fix_lat = config_a.latitude + (fix_y / meters_per_deg_lat)
        fix_lon = config_a.longitude + (fix_x / meters_per_deg_lon)
        return (fix_lat, fix_lon, crossing_error_m)


class RdfService(QObject):
    rdf_report_received = Signal(dict)
    triangulated_fix_ready = Signal(dict)
    _triangulate_requested = Signal(dict, dict)
    _set_sensor_center_requested = Signal(float, float)
    _configure_station_requested = Signal(int, float, float, float, float)
    _set_distance_tolerance_requested = Signal(float)

    def __init__(self, *, time_window_seconds: int = 60) -> None:
        super().__init__()
        self._window_seconds = max(time_window_seconds, 1)
        self._frequency_tolerance_hz = 0.0
        self._reports_by_station: dict[int, deque[RdfReport]] = {
            1: deque(),
            2: deque(),
        }

        self._thread = QThread(self)
        self._worker = RdfTriangulationWorker()
        self._worker.moveToThread(self._thread)
        self._worker.triangulation_ready.connect(self.triangulated_fix_ready.emit)
        self._triangulate_requested.connect(self._worker.triangulate)
        self._set_sensor_center_requested.connect(self._worker.set_sensor_center)
        self._configure_station_requested.connect(self._worker.configure_station)
        self._set_distance_tolerance_requested.connect(self._worker.set_distance_tolerance)
        self._thread.start()

    @Slot(float, float)
    def set_sensor_center(self, latitude: float, longitude: float) -> None:
        self._set_sensor_center_requested.emit(latitude, longitude)

    @Slot(int, float, float, float, float)
    def configure_station(
        self,
        station_id: int,
        latitude: float,
        longitude: float,
        altitude_m: float,
        bearing_offset_deg: float,
    ) -> None:
        self._configure_station_requested.emit(
            station_id,
            latitude,
            longitude,
            altitude_m,
            bearing_offset_deg,
        )

    @Slot(float)
    def set_frequency_tolerance(self, frequency_tolerance_hz: float) -> None:
        self._frequency_tolerance_hz = max(frequency_tolerance_hz, 0.0)

    @Slot(float)
    def set_distance_tolerance(self, distance_tolerance_m: float) -> None:
        self._set_distance_tolerance_requested.emit(max(distance_tolerance_m, 0.0))

    @Slot(dict)
    def submit_report(self, payload: dict[str, float | int | str]) -> None:
        report = self._parse_report(payload)
        if report is None:
            return

        self._trim_expired(reference_time=report.timestamp)
        station_queue = self._reports_by_station.setdefault(report.station_id, deque())
        station_queue.append(report)

        report_payload = {
            SCHEMA.DATETIME: report.timestamp.isoformat(),
            SCHEMA.STATION_ID: report.station_id,
            SCHEMA.FREQUENCY: report.frequency_hz,
            SCHEMA.BEARING: report.bearing_deg,
        }
        self.rdf_report_received.emit(report_payload)

        counterpart_station = 1 if report.station_id == 2 else 2
        counterpart_report = self._find_match(counterpart_station, report)
        if counterpart_report is None:
            return

        self._triangulate_requested.emit(
            {
                SCHEMA.STATION_ID: report.station_id,
                SCHEMA.FREQUENCY: report.frequency_hz,
                SCHEMA.BEARING: report.bearing_deg,
                SCHEMA.DATETIME: report.timestamp.isoformat(),
            },
            {
                SCHEMA.STATION_ID: counterpart_report.station_id,
                SCHEMA.FREQUENCY: counterpart_report.frequency_hz,
                SCHEMA.BEARING: counterpart_report.bearing_deg,
                SCHEMA.DATETIME: counterpart_report.timestamp.isoformat(),
            },
        )

    def stop(self) -> None:
        if self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(2000)

    def _parse_report(self, payload: dict[str, float | int | str]) -> RdfReport | None:
        try:
            station_id = int(payload[SCHEMA.STATION_ID])
            frequency_hz = float(payload[SCHEMA.FREQUENCY])
            bearing_deg = float(payload[SCHEMA.BEARING])
        except (KeyError, TypeError, ValueError):
            return None

        if station_id not in (1, 2):
            return None

        timestamp_raw = payload.get(SCHEMA.DATETIME)
        if isinstance(timestamp_raw, str):
            try:
                timestamp = datetime.fromisoformat(timestamp_raw)
            except ValueError:
                timestamp = datetime.now(UTC)
        else:
            timestamp = datetime.now(UTC)

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)

        bearing_deg = bearing_deg % 360.0
        if frequency_hz <= 0.0:
            return None

        return RdfReport(
            station_id=station_id,
            frequency_hz=frequency_hz,
            bearing_deg=bearing_deg,
            timestamp=timestamp,
        )

    def _trim_expired(self, reference_time: datetime) -> None:
        cutoff = reference_time - timedelta(seconds=self._window_seconds)
        for station_queue in self._reports_by_station.values():
            while station_queue and station_queue[0].timestamp < cutoff:
                station_queue.popleft()

    def _find_match(self, station_id: int, report: RdfReport) -> RdfReport | None:
        station_queue = self._reports_by_station.get(station_id)
        if station_queue is None:
            return None

        best_match: RdfReport | None = None
        best_delta_seconds = float('inf')
        for candidate in station_queue:
            if abs(candidate.frequency_hz - report.frequency_hz) > self._frequency_tolerance_hz:
                continue
            delta_seconds = abs((report.timestamp - candidate.timestamp).total_seconds())
            if delta_seconds <= self._window_seconds and delta_seconds < best_delta_seconds:
                best_match = candidate
                best_delta_seconds = delta_seconds

        return best_match


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    sin_dphi = math.sin(d_phi / 2.0)
    sin_dlambda = math.sin(d_lambda / 2.0)
    a = sin_dphi * sin_dphi + math.cos(phi1) * math.cos(phi2) * sin_dlambda * sin_dlambda
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return radius * c
