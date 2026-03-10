from typing import Any

from PySide6.QtCore import Qt, Signal
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
		content_layout.addLayout(self._labeled_row('Target Name', self._target_name_input))
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


class SimulatorView(QWidget):
	start_simulation_requested = Signal(dict)
	stop_simulation_requested = Signal(int)
	visibility_changed = Signal(bool)

	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent, Qt.WindowType.Window)
		self.setWindowTitle('Simulator')
		self.resize(420, 500)

		layout = QVBoxLayout(self)

		self.target_sections: list[TargetSection] = [
			TargetSection(title='Target 1', default_target_id=1),
			TargetSection(title='Target 2', default_target_id=2),
		]

		for section in self.target_sections:
			section.start_requested.connect(self.start_simulation_requested.emit)
			section.stop_requested.connect(self.stop_simulation_requested.emit)
			layout.addWidget(section)

		layout.addStretch()

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
