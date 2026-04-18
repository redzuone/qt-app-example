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

        self._rdf_station_1_latitude_input = QDoubleSpinBox(self)
        self._rdf_station_1_latitude_input.setRange(-90.0, 90.0)
        self._rdf_station_1_latitude_input.setDecimals(6)
        self._rdf_station_1_latitude_input.setSingleStep(0.0001)
        self._rdf_station_1_latitude_input.setValue(app_settings.rdf_station_1_latitude)

        self._rdf_station_1_longitude_input = QDoubleSpinBox(self)
        self._rdf_station_1_longitude_input.setRange(-180.0, 180.0)
        self._rdf_station_1_longitude_input.setDecimals(6)
        self._rdf_station_1_longitude_input.setSingleStep(0.0001)
        self._rdf_station_1_longitude_input.setValue(app_settings.rdf_station_1_longitude)

        self._rdf_station_1_altitude_input = QDoubleSpinBox(self)
        self._rdf_station_1_altitude_input.setRange(-1000.0, 100000.0)
        self._rdf_station_1_altitude_input.setDecimals(1)
        self._rdf_station_1_altitude_input.setSingleStep(1.0)
        self._rdf_station_1_altitude_input.setValue(app_settings.rdf_station_1_altitude_m)

        self._rdf_station_1_bearing_offset_input = QDoubleSpinBox(self)
        self._rdf_station_1_bearing_offset_input.setRange(-360.0, 360.0)
        self._rdf_station_1_bearing_offset_input.setDecimals(3)
        self._rdf_station_1_bearing_offset_input.setSingleStep(0.1)
        self._rdf_station_1_bearing_offset_input.setValue(
            app_settings.rdf_station_1_bearing_offset_deg
        )

        self._rdf_station_2_latitude_input = QDoubleSpinBox(self)
        self._rdf_station_2_latitude_input.setRange(-90.0, 90.0)
        self._rdf_station_2_latitude_input.setDecimals(6)
        self._rdf_station_2_latitude_input.setSingleStep(0.0001)
        self._rdf_station_2_latitude_input.setValue(app_settings.rdf_station_2_latitude)

        self._rdf_station_2_longitude_input = QDoubleSpinBox(self)
        self._rdf_station_2_longitude_input.setRange(-180.0, 180.0)
        self._rdf_station_2_longitude_input.setDecimals(6)
        self._rdf_station_2_longitude_input.setSingleStep(0.0001)
        self._rdf_station_2_longitude_input.setValue(app_settings.rdf_station_2_longitude)

        self._rdf_station_2_altitude_input = QDoubleSpinBox(self)
        self._rdf_station_2_altitude_input.setRange(-1000.0, 100000.0)
        self._rdf_station_2_altitude_input.setDecimals(1)
        self._rdf_station_2_altitude_input.setSingleStep(1.0)
        self._rdf_station_2_altitude_input.setValue(app_settings.rdf_station_2_altitude_m)

        self._rdf_station_2_bearing_offset_input = QDoubleSpinBox(self)
        self._rdf_station_2_bearing_offset_input.setRange(-360.0, 360.0)
        self._rdf_station_2_bearing_offset_input.setDecimals(3)
        self._rdf_station_2_bearing_offset_input.setSingleStep(0.1)
        self._rdf_station_2_bearing_offset_input.setValue(
            app_settings.rdf_station_2_bearing_offset_deg
        )

        self._rdf_frequency_tolerance_input = QDoubleSpinBox(self)
        self._rdf_frequency_tolerance_input.setRange(0.0, 1_000_000_000.0)
        self._rdf_frequency_tolerance_input.setDecimals(6)
        self._rdf_frequency_tolerance_input.setSingleStep(1.0)
        self._rdf_frequency_tolerance_input.setValue(app_settings.rdf_frequency_tolerance_hz)

        self._rdf_distance_tolerance_input = QDoubleSpinBox(self)
        self._rdf_distance_tolerance_input.setRange(0.0, 10_000_000.0)
        self._rdf_distance_tolerance_input.setDecimals(1)
        self._rdf_distance_tolerance_input.setSingleStep(10.0)
        self._rdf_distance_tolerance_input.setValue(app_settings.rdf_distance_tolerance_m)

        form_layout = QFormLayout()
        form_layout.addRow('Sensor centre latitude', self._sensor_center_latitude_input)
        form_layout.addRow('Sensor centre longitude', self._sensor_center_longitude_input)
        form_layout.addRow('Map brightness', self._map_brightness_input)
        form_layout.addRow('RDF station 1 latitude', self._rdf_station_1_latitude_input)
        form_layout.addRow('RDF station 1 longitude', self._rdf_station_1_longitude_input)
        form_layout.addRow('RDF station 1 altitude (m)', self._rdf_station_1_altitude_input)
        form_layout.addRow(
            'RDF station 1 bearing offset (deg)',
            self._rdf_station_1_bearing_offset_input,
        )
        form_layout.addRow('RDF station 2 latitude', self._rdf_station_2_latitude_input)
        form_layout.addRow('RDF station 2 longitude', self._rdf_station_2_longitude_input)
        form_layout.addRow('RDF station 2 altitude (m)', self._rdf_station_2_altitude_input)
        form_layout.addRow(
            'RDF station 2 bearing offset (deg)',
            self._rdf_station_2_bearing_offset_input,
        )
        form_layout.addRow('RDF frequency tolerance (Hz)', self._rdf_frequency_tolerance_input)
        form_layout.addRow('RDF distance tolerance (m)', self._rdf_distance_tolerance_input)

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

    def rdf_station_1(self) -> tuple[float, float, float, float]:
        return (
            self._rdf_station_1_latitude_input.value(),
            self._rdf_station_1_longitude_input.value(),
            self._rdf_station_1_altitude_input.value(),
            self._rdf_station_1_bearing_offset_input.value(),
        )

    def rdf_station_2(self) -> tuple[float, float, float, float]:
        return (
            self._rdf_station_2_latitude_input.value(),
            self._rdf_station_2_longitude_input.value(),
            self._rdf_station_2_altitude_input.value(),
            self._rdf_station_2_bearing_offset_input.value(),
        )

    def rdf_frequency_tolerance_hz(self) -> float:
        return self._rdf_frequency_tolerance_input.value()

    def rdf_distance_tolerance_m(self) -> float:
        return self._rdf_distance_tolerance_input.value()