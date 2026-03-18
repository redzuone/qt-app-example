from dataclasses import dataclass

from PySide6.QtCore import QSettings

from app.constants import APP_ID, APP_ORGANIZATION


@dataclass
class AppSettings:
    sensor_latitude: float = 0.0
    sensor_longitude: float = 0.0
    map_brightness: float = 1.0


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
    return AppSettings(
        sensor_latitude=_coerce_float(
            qs.value('sensor/center/latitude', qs.value('map/center/latitude', 0.0)),
            0.0,
        ),
        sensor_longitude=_coerce_float(
            qs.value('sensor/center/longitude', qs.value('map/center/longitude', 0.0)),
            0.0,
        ),
        map_brightness=_clamp_float(
            _coerce_float(qs.value('map/brightness', 1.0), 1.0),
            0.2,
            1.0,
        ),
    )


def save_settings(qs: QSettings, settings: AppSettings) -> None:
    """Persist the typed settings dataclass."""
    qs.setValue('sensor/center/latitude', settings.sensor_latitude)
    qs.setValue('sensor/center/longitude', settings.sensor_longitude)
    qs.setValue('map/brightness', _clamp_float(settings.map_brightness, 0.2, 1.0))
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
