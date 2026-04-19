from typing import Any

import numpy as np
import pyqtgraph as pg  # type: ignore
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent, QTransform
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.views._detachable_tab import DetachableTab


class WaterfallPlot(QWidget):
    """RF waterfall display intended to live inside a :class:`DetachableTab`.

    Accepts ``(freq_ghz, power_dbm)`` tuples via :meth:`update_waterfall`.
    Missing bins should be ``np.nan``; they map to the darkest colormap colour,
    making gaps visually distinct from low-but-valid signal.

    The internal history buffer is lazily initialised on the first update so
    the view adapts to whatever frequency grid arrives.
    """

    pop_requested = Signal()

    _HISTORY = 180
    _POWER_MIN = -120.0
    _POWER_MAX = -20.0

    def __init__(self) -> None:
        super().__init__()

        self._bins: int | None = None
        self._waterfall_data: np.ndarray | None = None

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
        self._plot.showGrid(x=False, y=False)
        self._plot.setLabel('bottom', 'Frequency', units='GHz')
        self._plot.setLabel('left', 'Time (newest at bottom)')
        self._plot.setXRange(0.0, 6.0, padding=0.01)
        self._plot.setYRange(0, self._HISTORY, padding=0.0)

        self._image = pg.ImageItem(axisOrder='row-major')
        self._plot.addItem(self._image)

        cmap = pg.colormap.get('CET-L9')
        lut = cmap.getLookupTable(0.0, 1.0, 256)
        self._image.setLookupTable(lut)
        # Levels span the valid dBm range; NaN bins map to the darkest colour.
        self._image.setLevels((self._POWER_MIN, self._POWER_MAX))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addLayout(controls)
        layout.addWidget(self._plot)

    def set_popped_out(self, popped: bool) -> None:
        self._pop_btn.setChecked(popped)
        self._pop_btn.setText('Pop In' if popped else 'Pop Out')

    def _init_buffer(self, bins: int, freq_min_ghz: float, freq_max_ghz: float) -> None:
        """(Re-)initialise the history buffer and image transform for *bins* bins."""
        self._bins = bins
        # Fill with NaN so uninitialised rows show as "no data".
        self._waterfall_data = np.full((self._HISTORY, bins), np.nan, dtype=np.float32)

        # Map image pixels to scene (frequency, row) coordinates.
        # Each column covers one frequency bin; each row is one time step.
        freq_step = (freq_max_ghz - freq_min_ghz) / bins
        transform = QTransform()
        transform.translate(freq_min_ghz, 0.0)
        transform.scale(freq_step, 1.0)
        self._image.resetTransform()
        self._image.setTransform(transform)
        self._image.setAutoDownsample(False)

    def update_waterfall(self, data: tuple[np.ndarray, np.ndarray]) -> None:
        if self._hold_btn.isChecked():
            return
        freq_ghz, power_dbm = data
        bins = len(power_dbm)

        if self._bins != bins or self._waterfall_data is None:
            f_min = float(freq_ghz[0])
            f_max = float(freq_ghz[-1])
            # Extend the right edge by one bin-width so the last bin has full width.
            step = (f_max - f_min) / max(bins - 1, 1)
            self._init_buffer(bins, f_min, f_max + step)

        assert self._waterfall_data is not None
        self._waterfall_data = np.roll(self._waterfall_data, -1, axis=0)
        self._waterfall_data[-1, :] = power_dbm
        self._image.setImage(self._waterfall_data, autoLevels=False)


class _WaterfallStationTab(DetachableTab):
    def __init__(self, station_id: int) -> None:
        plot = WaterfallPlot()
        super().__init__(
            content=plot,
            window_title=f'Waterfall — Station {station_id}',
            placeholder_text=f'Station {station_id} waterfall is shown in a separate window.',
        )
        self._plot = plot

    def update_waterfall(self, data: tuple[np.ndarray, np.ndarray]) -> None:
        self._plot.update_waterfall(data)


class WaterfallView(QWidget):
    """RF waterfall display with per-station tabs and detachable plots."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle('Waterfall')
        self.resize(640, 480)

        self._tabs = QTabWidget()
        self._tabs.setTabPosition(QTabWidget.TabPosition.West)

        self._station_tabs: dict[int, _WaterfallStationTab] = {}
        for station_id in (1, 2):
            tab = _WaterfallStationTab(station_id=station_id)
            self._station_tabs[station_id] = tab
            self._tabs.addTab(tab, f'Station {station_id}')

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._tabs)

    def update_waterfall(self, data: tuple[Any, np.ndarray, np.ndarray]) -> None:
        station_id, freq_ghz, power_dbm = data
        tab = self._station_tabs.get(int(station_id))
        if tab is not None:
            tab.update_waterfall((freq_ghz, power_dbm))

    def closeEvent(self, event: QCloseEvent) -> None:
        for tab in self._station_tabs.values():
            tab._pop_in()
        event.ignore()
        self.hide()
