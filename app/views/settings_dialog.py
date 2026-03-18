from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QVBoxLayout,
    QWidget,
)

from app.utils.app_settings import AppSettings


class SettingsDialog(QDialog):
    def __init__(self, app_settings: AppSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle('Settings')
        self.setModal(True)

        self._sensor_center_latitude_input = QDoubleSpinBox(self)
        self._sensor_center_latitude_input.setRange(-90.0, 90.0)
        self._sensor_center_latitude_input.setDecimals(6)
        self._sensor_center_latitude_input.setSingleStep(0.0001)
        self._sensor_center_latitude_input.setValue(app_settings.sensor_latitude)

        self._sensor_center_longitude_input = QDoubleSpinBox(self)
        self._sensor_center_longitude_input.setRange(-180.0, 180.0)
        self._sensor_center_longitude_input.setDecimals(6)
        self._sensor_center_longitude_input.setSingleStep(0.0001)
        self._sensor_center_longitude_input.setValue(app_settings.sensor_longitude)

        self._map_brightness_input = QDoubleSpinBox(self)
        self._map_brightness_input.setRange(0.2, 1.0)
        self._map_brightness_input.setDecimals(2)
        self._map_brightness_input.setSingleStep(0.05)
        self._map_brightness_input.setValue(app_settings.map_brightness)

        form_layout = QFormLayout()
        form_layout.addRow('Sensor centre latitude', self._sensor_center_latitude_input)
        form_layout.addRow('Sensor centre longitude', self._sensor_center_longitude_input)
        form_layout.addRow('Map brightness', self._map_brightness_input)

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

    def map_brightness(self) -> float:
        return self._map_brightness_input.value()