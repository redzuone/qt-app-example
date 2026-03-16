from PySide6.QtCore import QSettings

from app.constants import APP_ID, APP_ORGANIZATION


def create_app_settings() -> QSettings:
    """Create user-scoped INI settings for the app.
    """
    return QSettings(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        APP_ORGANIZATION,
        APP_ID,
    )
