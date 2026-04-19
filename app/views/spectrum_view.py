from typing import Any

import numpy as np
import pyqtgraph as pg  # type: ignore
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.views._detachable_tab import DetachableTab


class SpectrumPlot(QWidget):
    """RF spectrum display intended to live inside a :class:`DetachableTab`.

    Accepts ``(freq_ghz, power_dbm)`` tuples via :meth:`update_spectrum`.
    Missing bins should be ``np.nan``; pyqtgraph renders them as line breaks.
    """

    pop_requested = Signal()

    _POWER_MIN = -120.0
    _POWER_MAX = -20.0

    def __init__(self) -> None:
        super().__init__()

        # Controls row
        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(4)

        self._hold_btn = QPushButton('Hold')
        self._hold_btn.setCheckable(True)
        controls.addWidget(self._hold_btn)

        self._pop_btn = QPushButton('Pop Out')
        self._pop_btn.setCheckable(True)
        self._pop_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._pop_btn.clicked.connect(self.pop_requested)
        controls.addStretch(1)
        controls.addWidget(self._pop_btn)

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
        layout.addLayout(controls)
        layout.addWidget(self._plot)

    def set_popped_out(self, popped: bool) -> None:
        self._pop_btn.setChecked(popped)
        self._pop_btn.setText('Pop In' if popped else 'Pop Out')

    def update_spectrum(self, data: tuple[np.ndarray, np.ndarray]) -> None:
        if self._hold_btn.isChecked():
            return
        freq_ghz, power_dbm = data
        self._curve.setData(freq_ghz, power_dbm)


class _SpectrumStationTab(DetachableTab):
    def __init__(self, station_id: int) -> None:
        plot = SpectrumPlot()
        super().__init__(
            content=plot,
            window_title=f'Spectrum — Station {station_id}',
            placeholder_text=f'Station {station_id} spectrum is shown in a separate window.',
        )
        self._plot = plot

    def update_spectrum(self, data: tuple[np.ndarray, np.ndarray]) -> None:
        self._plot.update_spectrum(data)


class SpectrumView(QWidget):
    """RF spectrum display with per-station tabs and detachable plots."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle('Spectrum')
        self.resize(640, 480)

        self._tabs = QTabWidget()
        self._tabs.setTabPosition(QTabWidget.TabPosition.West)

        self._station_tabs: dict[int, _SpectrumStationTab] = {}
        for station_id in (1, 2):
            tab = _SpectrumStationTab(station_id=station_id)
            self._station_tabs[station_id] = tab
            self._tabs.addTab(tab, f'Station {station_id}')

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._tabs)

    def update_spectrum(self, data: tuple[Any, np.ndarray, np.ndarray]) -> None:
        station_id, freq_ghz, power_dbm = data
        tab = self._station_tabs.get(int(station_id))
        if tab is not None:
            tab.update_spectrum((freq_ghz, power_dbm))

    def closeEvent(self, event: QCloseEvent) -> None:
        for tab in self._station_tabs.values():
            tab._pop_in()
        event.ignore()
        self.hide()
