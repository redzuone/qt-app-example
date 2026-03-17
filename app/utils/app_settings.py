from PySide6.QtCore import QSettings

from app.constants import APP_ID, APP_ORGANIZATION

DEFAULT_SENSOR_CENTER_LATITUDE = 0.0
DEFAULT_SENSOR_CENTER_LONGITUDE = 0.0


def create_app_settings() -> QSettings:
    """Create user-scoped INI settings for the app.
    """
    return QSettings(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        APP_ORGANIZATION,
        APP_ID,
    )


def get_sensor_center(settings: QSettings) -> tuple[float, float]:
    """Return the persisted sensor center, falling back to the app default."""
    latitude_value = settings.value(
        'sensor/center/latitude',
        settings.value('map/center/latitude', DEFAULT_SENSOR_CENTER_LATITUDE),
    )
    longitude_value = settings.value(
        'sensor/center/longitude',
        settings.value('map/center/longitude', DEFAULT_SENSOR_CENTER_LONGITUDE),
    )

    latitude = _coerce_float(latitude_value, DEFAULT_SENSOR_CENTER_LATITUDE)
    longitude = _coerce_float(longitude_value, DEFAULT_SENSOR_CENTER_LONGITUDE)

    return latitude, longitude


def set_sensor_center(settings: QSettings, latitude: float, longitude: float) -> None:
    settings.setValue('sensor/center/latitude', latitude)
    settings.setValue('sensor/center/longitude', longitude)
    settings.sync()


def _coerce_float(value: object, fallback: float) -> float:
    if isinstance(value, (int, float, str)):
        try:
            return float(value)
        except ValueError:
            return fallback

    return fallback
