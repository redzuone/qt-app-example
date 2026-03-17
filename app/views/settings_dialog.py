from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QVBoxLayout,
    QWidget,
)

from app.utils.app_settings import get_sensor_center


class SettingsDialog(QDialog):
    def __init__(self, settings: QSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle('Settings')
        self.setModal(True)

        latitude, longitude = get_sensor_center(settings)

        self._sensor_center_latitude_input = QDoubleSpinBox(self)
        self._sensor_center_latitude_input.setRange(-90.0, 90.0)
        self._sensor_center_latitude_input.setDecimals(6)
        self._sensor_center_latitude_input.setSingleStep(0.0001)
        self._sensor_center_latitude_input.setValue(latitude)

        self._sensor_center_longitude_input = QDoubleSpinBox(self)
        self._sensor_center_longitude_input.setRange(-180.0, 180.0)
        self._sensor_center_longitude_input.setDecimals(6)
        self._sensor_center_longitude_input.setSingleStep(0.0001)
        self._sensor_center_longitude_input.setValue(longitude)

        form_layout = QFormLayout()
        form_layout.addRow('Sensor centre latitude', self._sensor_center_latitude_input)
        form_layout.addRow('Sensor centre longitude', self._sensor_center_longitude_input)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form_layout)
        layout.addWidget(button_box)

    def sensor_center(self) -> tuple[float, float]:
        return (
            self._sensor_center_latitude_input.value(),
            self._sensor_center_longitude_input.value(),
        )