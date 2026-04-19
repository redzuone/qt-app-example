from datetime import UTC, datetime
import random
from typing import Any

from app.constants.data_schema import SCHEMA
from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtGui import QCloseEvent, QHideEvent, QShowEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class TargetSection(QWidget):
    start_requested = Signal(dict)
    stop_requested = Signal(int)

    def __init__(self, title: str, default_target_id: int) -> None:
        super().__init__()
        self._title = title
        self._default_target_id = default_target_id
        self._is_running = False

        self._init_widgets()
        self._init_layout()
        self._connect_signals()
        self._on_toggle_section(False)

    def _init_widgets(self) -> None:
        self._toggle_button = QPushButton()
        self._toggle_button.setCheckable(True)
        self._toggle_button.setChecked(False)

        self._content = QWidget()

        self._target_name_input = QLineEdit()
        self._target_name_input.setText(f'Target {self._default_target_id}')
        self._target_name_input.setPlaceholderText('Target Name')

        self._latitude_input = QDoubleSpinBox()
        self._latitude_input.setRange(-90.0, 90.0)
        self._latitude_input.setDecimals(6)
        self._latitude_input.setSingleStep(0.0001)

        self._longitude_input = QDoubleSpinBox()
        self._longitude_input.setRange(-180.0, 180.0)
        self._longitude_input.setDecimals(6)
        self._longitude_input.setSingleStep(0.0001)

        self._target_id_input = QSpinBox()
        self._target_id_input.setRange(1, 999999)
        self._target_id_input.setValue(self._default_target_id)

        self._static_checkbox = QCheckBox('Static')
        self._static_checkbox.setChecked(True)

        self._type_combo = QComboBox()
        self._type_combo.addItems(['raw_data', 'vehicle', 'target'])

        self._start_stop_button = QPushButton('Start')

    def _init_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(self._toggle_button)

        content_layout = QVBoxLayout(self._content)
        content_layout.addLayout(
            self._labeled_row('Target Name', self._target_name_input)
        )
        content_layout.addLayout(self._labeled_row('Latitude', self._latitude_input))
        content_layout.addLayout(self._labeled_row('Longitude', self._longitude_input))
        content_layout.addLayout(self._labeled_row('Target ID', self._target_id_input))
        content_layout.addLayout(self._labeled_row('Type', self._type_combo))
        content_layout.addWidget(self._static_checkbox)
        content_layout.addWidget(self._start_stop_button)

        layout.addWidget(self._content)

    def _connect_signals(self) -> None:
        self._toggle_button.toggled.connect(self._on_toggle_section)
        self._start_stop_button.clicked.connect(self._on_start_stop)

    def _labeled_row(self, label: str, widget: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel(label, self))
        row.addWidget(widget)
        return row

    def _on_toggle_section(self, expanded: bool) -> None:
        self._content.setVisible(expanded)
        self._toggle_button.setText(
            f'Hide {self._title}' if expanded else f'Show {self._title}'
        )

    def _build_target_data(self) -> dict[str, Any]:
        return {
            'target_name': self._target_name_input.text().strip(),
            'target_id': self._target_id_input.value(),
            'latitude': self._latitude_input.value(),
            'longitude': self._longitude_input.value(),
            'type': self._type_combo.currentText(),
            'static': self._static_checkbox.isChecked(),
        }

    def _on_start_stop(self) -> None:
        if not self._is_running:
            self.start_requested.emit(self._build_target_data())
            self._is_running = True
            return

        self.stop_requested.emit(self._target_id_input.value())
        self._is_running = False

    def set_running(self, running: bool) -> None:
        self._is_running = running
        self._start_stop_button.setText('Stop' if running else 'Start')

    def target_id(self) -> int:
        return self._target_id_input.value()

    def set_coordinates(self, latitude: float, longitude: float) -> None:
        self._latitude_input.setValue(latitude)
        self._longitude_input.setValue(longitude)


class RdfStationSection(QWidget):
    rdf_send_requested = Signal(dict)

    def __init__(self, station_id: int, default_bearing_deg: float) -> None:
        super().__init__()
        self._station_id = station_id

        self._frequency_input = QDoubleSpinBox()
        self._frequency_input.setRange(1.0, 6_000_000_000.0)
        self._frequency_input.setDecimals(0)
        self._frequency_input.setSingleStep(100.0)
        self._frequency_input.setValue(2_400_000_000.0)

        self._bearing_input = QDoubleSpinBox()
        self._bearing_input.setRange(0.0, 359.999)
        self._bearing_input.setDecimals(0)
        self._bearing_input.setSingleStep(1.0)
        self._bearing_input.setValue(default_bearing_deg)

        self._send_button = QPushButton(f'Send Station {station_id}')
        self._send_button.clicked.connect(self._on_send_clicked)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f'RDF Station {station_id}', self))
        layout.addLayout(self._labeled_row('Frequency (Hz)', self._frequency_input))
        layout.addLayout(self._labeled_row('Bearing (deg)', self._bearing_input))
        layout.addWidget(self._send_button)

    def _labeled_row(self, label: str, widget: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel(label, self))
        row.addWidget(widget)
        return row

    def _on_send_clicked(self) -> None:
        self.rdf_send_requested.emit(
            {
                SCHEMA.STATION_ID: self._station_id,
                SCHEMA.FREQUENCY: self._frequency_input.value(),
                SCHEMA.BEARING: self._bearing_input.value(),
                SCHEMA.DATETIME: datetime.now(UTC).isoformat(),
            }
        )


class SimulatorView(QWidget):
    start_simulation_requested = Signal(dict)
    stop_simulation_requested = Signal(int)
    stop_all_simulation_requested = Signal()
    rdf_send_requested = Signal(dict)
    visibility_changed = Signal(bool)
    spectrum_start_requested = Signal()
    spectrum_stop_requested = Signal()
    spectrum_station_changed = Signal(int)

    def __init__(self, settings: QSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self._settings = settings
        self.setWindowTitle('Simulator')
        self.resize(420, 500)
        self._next_auto_target_id = 1000
        self._random = random.Random()

        layout = QVBoxLayout(self)

        self._simulate_multiple_count = QSpinBox()
        self._simulate_multiple_count.setRange(1, 200)
        self._simulate_multiple_count.setValue(5)

        self._simulate_multiple_button = QPushButton('Simulate multiple')
        self._simulate_multiple_button.clicked.connect(self._on_simulate_multiple)
        self._stop_all_button = QPushButton('Stop all')
        self._stop_all_button.clicked.connect(self.stop_all_simulation_requested.emit)

        multi_row = QHBoxLayout()
        multi_row.addWidget(QLabel('Count', self))
        multi_row.addWidget(self._simulate_multiple_count)
        multi_row.addWidget(self._simulate_multiple_button)
        multi_row.addWidget(self._stop_all_button)
        layout.addLayout(multi_row)

        self._spectrum_button = QPushButton('Start')
        self._spectrum_button.setCheckable(True)
        self._spectrum_button.clicked.connect(self._on_spectrum_toggle)
        self._station_combo = QComboBox()
        self._station_combo.addItems(['Station 1', 'Station 2'])
        self._station_combo.currentIndexChanged.connect(
            lambda idx: self.spectrum_station_changed.emit(idx + 1)
        )
        spectrum_row = QHBoxLayout()
        spectrum_row.addWidget(QLabel('Spectrum Simulator', self))
        spectrum_row.addWidget(self._station_combo)
        spectrum_row.addWidget(self._spectrum_button)
        layout.addLayout(spectrum_row)

        self.target_sections: list[TargetSection] = [
            TargetSection(title='Target 1', default_target_id=1),
            TargetSection(title='Target 2', default_target_id=2),
        ]

        for section in self.target_sections:
            section.start_requested.connect(self._on_start_requested)
            section.stop_requested.connect(self.stop_simulation_requested.emit)
            layout.addWidget(section)

        self._rdf_station_sections = [
            RdfStationSection(station_id=1, default_bearing_deg=45.0),
            RdfStationSection(station_id=2, default_bearing_deg=315.0),
        ]
        for rdf_section in self._rdf_station_sections:
            rdf_section.rdf_send_requested.connect(self.rdf_send_requested.emit)
            layout.addWidget(rdf_section)

        layout.addStretch()
        self._load_recent_coordinates()

    def _on_start_requested(self, target_data: dict[str, Any]) -> None:
        self._save_recent_coordinates(target_data)
        self.start_simulation_requested.emit(target_data)

    def _on_spectrum_toggle(self) -> None:
        if self._spectrum_button.isChecked():
            self._spectrum_button.setText('Stop')
            self.spectrum_start_requested.emit()
        else:
            self._spectrum_button.setText('Start')
            self.spectrum_stop_requested.emit()

    def _on_simulate_multiple(self) -> None:
        count = self._simulate_multiple_count.value()
        base_latitude_value = self._settings.value(
            'simulator/recent/latitude',
            0.0,
            type=float,
        )
        base_longitude_value = self._settings.value(
            'simulator/recent/longitude',
            0.0,
            type=float,
        )

        base_latitude = 0.0
        base_longitude = 0.0

        if isinstance(base_latitude_value, (int, float, str)):
            try:
                base_latitude = float(base_latitude_value)
            except TypeError, ValueError:
                base_latitude = 0.0

        if isinstance(base_longitude_value, (int, float, str)):
            try:
                base_longitude = float(base_longitude_value)
            except TypeError, ValueError:
                base_longitude = 0.0

        for _ in range(count):
            target_id = self._next_available_auto_target_id()
            latitude = base_latitude + self._random.uniform(-0.03, 0.03)
            longitude = base_longitude + self._random.uniform(-0.03, 0.03)

            latitude = max(min(latitude, 89.9), -89.9)
            longitude = ((longitude + 180.0) % 360.0) - 180.0

            target_data = {
                'target_name': f'Target {target_id}',
                'target_id': target_id,
                'latitude': latitude,
                'longitude': longitude,
                'type': self._random.choice(['vehicle', 'target']),
                'static': False,
            }
            self._on_start_requested(target_data)

    def _next_available_auto_target_id(self) -> int:
        manual_ids = {section.target_id() for section in self.target_sections}
        while self._next_auto_target_id in manual_ids:
            self._next_auto_target_id += 1

        target_id = self._next_auto_target_id
        self._next_auto_target_id += 1
        return target_id

    def _save_recent_coordinates(self, target_data: dict[str, Any]) -> None:
        try:
            target_id = int(target_data['target_id'])
            latitude = float(target_data['latitude'])
            longitude = float(target_data['longitude'])
        except KeyError, TypeError, ValueError:
            return

        self._settings.setValue('simulator/recent/latitude', latitude)
        self._settings.setValue('simulator/recent/longitude', longitude)
        self._settings.setValue(f'simulator/recent/{target_id}/latitude', latitude)
        self._settings.setValue(f'simulator/recent/{target_id}/longitude', longitude)
        self._settings.sync()

    def _load_recent_coordinates(self) -> None:
        recent_latitude = self._settings.value('simulator/recent/latitude', type=float)
        recent_longitude = self._settings.value(
            'simulator/recent/longitude', type=float
        )

        for section in self.target_sections:
            target_id = section.target_id()
            latitude = self._settings.value(
                f'simulator/recent/{target_id}/latitude',
                recent_latitude,
                type=float,
            )
            longitude = self._settings.value(
                f'simulator/recent/{target_id}/longitude',
                recent_longitude,
                type=float,
            )

            if latitude is None or longitude is None:
                continue

            if not isinstance(latitude, (int, float, str)):
                continue
            if not isinstance(longitude, (int, float, str)):
                continue

            try:
                section.set_coordinates(
                    latitude=float(latitude),
                    longitude=float(longitude),
                )
            except TypeError, ValueError:
                continue

    def set_target_running(self, target_id: int, running: bool) -> None:
        for section in self.target_sections:
            if section.target_id() == target_id:
                section.set_running(running)
                break

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.visibility_changed.emit(True)

    def hideEvent(self, event: QHideEvent) -> None:
        super().hideEvent(event)
        self.visibility_changed.emit(False)

    def closeEvent(self, event: QCloseEvent) -> None:
        event.accept()
        self.hide()
