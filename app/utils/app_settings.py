from dataclasses import dataclass

from PySide6.QtCore import QSettings

from app.constants import APP_ID, APP_ORGANIZATION


@dataclass
class AppSettings:
    sensor_latitude: float = 0.0
    sensor_longitude: float = 0.0
    map_brightness: float = 1.0
    rdf_station_1_latitude: float = 0.0
    rdf_station_1_longitude: float = -0.01
    rdf_station_1_altitude_m: float = 0.0
    rdf_station_1_bearing_offset_deg: float = 0.0
    rdf_station_2_latitude: float = 0.0
    rdf_station_2_longitude: float = 0.01
    rdf_station_2_altitude_m: float = 0.0
    rdf_station_2_bearing_offset_deg: float = 0.0
    rdf_frequency_tolerance_hz: float = 0.0
    rdf_distance_tolerance_m: float = 1500.0


def create_app_settings() -> QSettings:
    """Create user-scoped INI settings for the app."""
    return QSettings(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        APP_ORGANIZATION,
        APP_ID,
    )


def load_settings(qs: QSettings) -> AppSettings:
    """Load persisted settings into a typed dataclass."""
    sensor_latitude = _coerce_float(
        qs.value('sensor/center/latitude', qs.value('map/center/latitude', 0.0)),
        0.0,
    )
    sensor_longitude = _coerce_float(
        qs.value('sensor/center/longitude', qs.value('map/center/longitude', 0.0)),
        0.0,
    )

    return AppSettings(
        sensor_latitude=sensor_latitude,
        sensor_longitude=sensor_longitude,
        map_brightness=_clamp_float(
            _coerce_float(qs.value('map/brightness', 1.0), 1.0),
            0.2,
            1.0,
        ),
        rdf_station_1_latitude=_coerce_float(
            qs.value('rdf/station/1/latitude', sensor_latitude),
            sensor_latitude,
        ),
        rdf_station_1_longitude=_coerce_float(
            qs.value('rdf/station/1/longitude', sensor_longitude - 0.01),
            sensor_longitude - 0.01,
        ),
        rdf_station_1_altitude_m=_coerce_float(
            qs.value('rdf/station/1/altitude_m', 0.0),
            0.0,
        ),
        rdf_station_1_bearing_offset_deg=_coerce_float(
            qs.value('rdf/station/1/bearing_offset_deg', 0.0),
            0.0,
        ),
        rdf_station_2_latitude=_coerce_float(
            qs.value('rdf/station/2/latitude', sensor_latitude),
            sensor_latitude,
        ),
        rdf_station_2_longitude=_coerce_float(
            qs.value('rdf/station/2/longitude', sensor_longitude + 0.01),
            sensor_longitude + 0.01,
        ),
        rdf_station_2_altitude_m=_coerce_float(
            qs.value('rdf/station/2/altitude_m', 0.0),
            0.0,
        ),
        rdf_station_2_bearing_offset_deg=_coerce_float(
            qs.value('rdf/station/2/bearing_offset_deg', 0.0),
            0.0,
        ),
        rdf_frequency_tolerance_hz=max(
            0.0,
            _coerce_float(qs.value('rdf/frequency_tolerance_hz', 0.0), 0.0),
        ),
        rdf_distance_tolerance_m=max(
            0.0,
            _coerce_float(qs.value('rdf/distance_tolerance_m', 1500.0), 1500.0),
        ),
    )


def save_settings(qs: QSettings, settings: AppSettings) -> None:
    """Persist the typed settings dataclass."""
    qs.setValue('sensor/center/latitude', settings.sensor_latitude)
    qs.setValue('sensor/center/longitude', settings.sensor_longitude)
    qs.setValue('map/brightness', _clamp_float(settings.map_brightness, 0.2, 1.0))
    qs.setValue('rdf/station/1/latitude', settings.rdf_station_1_latitude)
    qs.setValue('rdf/station/1/longitude', settings.rdf_station_1_longitude)
    qs.setValue('rdf/station/1/altitude_m', settings.rdf_station_1_altitude_m)
    qs.setValue('rdf/station/1/bearing_offset_deg', settings.rdf_station_1_bearing_offset_deg)
    qs.setValue('rdf/station/2/latitude', settings.rdf_station_2_latitude)
    qs.setValue('rdf/station/2/longitude', settings.rdf_station_2_longitude)
    qs.setValue('rdf/station/2/altitude_m', settings.rdf_station_2_altitude_m)
    qs.setValue('rdf/station/2/bearing_offset_deg', settings.rdf_station_2_bearing_offset_deg)
    qs.setValue(
        'rdf/frequency_tolerance_hz',
        max(0.0, settings.rdf_frequency_tolerance_hz),
    )
    qs.setValue(
        'rdf/distance_tolerance_m',
        max(0.0, settings.rdf_distance_tolerance_m),
    )
    qs.sync()


def _coerce_float(value: object, fallback: float) -> float:
    if isinstance(value, (int, float, str)):
        try:
            return float(value)
        except ValueError:
            return fallback

    return fallback


def _clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
