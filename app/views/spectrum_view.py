import numpy as np
import pyqtgraph as pg  # type: ignore
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget


class SpectrumView(QWidget):
	"""RF spectrum display.

	Accepts ``(freq_ghz, power_dbm)`` tuples via :meth:`update_spectrum`.
	Missing bins should be ``np.nan``; pyqtgraph renders them as line breaks.
	"""

	_POWER_MIN = -120.0
	_POWER_MAX = -20.0

	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent, Qt.WindowType.Window)
		self.setWindowTitle('Spectrum')
		self.resize(640, 480)

		self._plot = pg.PlotWidget()
		self._plot.showGrid(x=True, y=True, alpha=0.25)
		self._plot.setLabel('bottom', 'Frequency', units='GHz')
		self._plot.setLabel('left', 'Power', units='dBm')
		self._plot.setXRange(0.0, 6.0, padding=0.01)
		self._plot.setYRange(self._POWER_MIN, self._POWER_MAX, padding=0.02)

		# connect='finite' causes pyqtgraph to skip NaN values,
		# producing natural line breaks for missing-data gaps.
		self._curve = self._plot.plot(
			pen=pg.mkPen('#ffd166', width=1.6),
			connect='finite',
		)

		layout = QVBoxLayout(self)
		layout.setContentsMargins(4, 4, 4, 4)
		layout.addWidget(self._plot)

	def update_spectrum(self, data: tuple[np.ndarray, np.ndarray]) -> None:
		freq_ghz, power_dbm = data
		self._curve.setData(freq_ghz, power_dbm)
