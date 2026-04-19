from collections import defaultdict
from datetime import datetime
from typing import Any

import pyqtgraph as pg  # type: ignore
from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.constants.data_schema import SCHEMA
from app.utils.target_color import _TARGET_COLORS


class RDFBearingTimePlot(QWidget):
    def __init__(self, title: str) -> None:
        super().__init__()
        self._title = title

        # Raw data storage — keyed by exact freq_hz float
        self._times_by_freq: dict[float, list[float]] = defaultdict(list)
        self._bearings_by_freq: dict[float, list[float]] = defaultdict(list)
        self._meta_by_freq: dict[float, list[dict[str, Any]]] = defaultdict(list)

        # pyqtgraph series — keyed by exact freq_hz float
        self._series_by_freq: dict[float, dict[str, Any]] = {}
        self._color_by_freq: dict[float, str] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        # Controls row
        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(4)

        self._clear_btn = QPushButton('Clear')
        controls.addWidget(self._clear_btn)

        self._legend_btn = QPushButton('Show Legend')
        controls.addWidget(self._legend_btn)

        controls.addStretch(1)

        self._last_updated_label = QLabel()
        controls.addWidget(self._last_updated_label)

        self._pop_btn = QPushButton('Pop Out')
        self._pop_btn.setCheckable(True)
        self._pop_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        controls.addWidget(self._pop_btn)

        layout.addLayout(controls)

        # Plot widget
        date_axis = pg.DateAxisItem()
        self._plot_widget = pg.PlotWidget(axisItems={'bottom': date_axis})
        self._plot_widget.setLabel('left', 'Bearing (°)')
        self._plot_widget.setLabel('bottom', 'Time')
        self._plot_widget.setYRange(0, 360)
        self._plot_widget.setLimits(yMin=0, yMax=360)
        self._plot_widget.showGrid(x=True, y=True, alpha=0.25)
        self._plot_widget.setTitle(title)
        self._plot_widget.enableAutoRange(axis='x')
        self._legend = self._plot_widget.addLegend()
        self._configure_legend()
        layout.addWidget(self._plot_widget)

        self._hover_label = QLabel('Hover any plot to inspect detailed info.')
        layout.addWidget(self._hover_label)

        # Connections
        self._clear_btn.clicked.connect(self.clear)
        self._legend_btn.clicked.connect(self._toggle_legend)
        self._legend.setVisible(False)

    def _configure_legend(self) -> None:
        self._legend.setLabelTextSize('8pt')
        self._legend.layout.setHorizontalSpacing(6)
        self._legend.layout.setVerticalSpacing(0)

    def _get_color(self, freq_hz: float) -> str:
        if freq_hz not in self._color_by_freq:
            idx = len(self._color_by_freq) % len(_TARGET_COLORS)
            self._color_by_freq[freq_hz] = _TARGET_COLORS[idx]
        return self._color_by_freq[freq_hz]

    def _format_freq_label(self, freq_hz: float) -> str:
        mhz = freq_hz / 1_000_000.0
        return f'{mhz:.6f}'.rstrip('0').rstrip('.') + ' MHz'

    def _create_series(self, freq_hz: float) -> dict[str, Any]:
        color = self._get_color(freq_hz)
        label = self._format_freq_label(freq_hz)
        pen = pg.mkPen(color=color, width=2)
        brush = pg.mkBrush(color)

        line_item = self._plot_widget.plot([], [], pen=pen, name=label)
        scatter_item = pg.ScatterPlotItem(
            [],
            [],
            pen=pg.mkPen(color=color, width=1),
            brush=brush,
            size=7,
            hoverable=True,
            hoverPen=pg.mkPen(color=color, width=2),
            hoverBrush=brush,
            hoverSize=11,
        )
        scatter_item.sigHovered.connect(self._on_points_hovered)
        self._plot_widget.addItem(scatter_item)

        series = {
            'label': label,
            'line_item': line_item,
            'scatter_item': scatter_item,
        }
        self._series_by_freq[freq_hz] = series
        return series

    def set_popped_out(self, popped: bool) -> None:
        self._pop_btn.setChecked(popped)
        self._pop_btn.setText('Pop In' if popped else 'Pop Out')

    def _toggle_legend(self) -> None:
        visible = not self._legend.isVisible()
        self._legend.setVisible(visible)
        self._legend_btn.setText('Hide Legend' if visible else 'Show Legend')

    def _on_points_hovered(self, _: object, points: Any, __: object) -> None:
        if not hasattr(points, '__len__') or len(points) == 0:
            return
        data = points[0].data()
        if not isinstance(data, dict):
            return
        self._hover_label.setText(
            f"Freq {data['freq_label']} | Bearing {data['bearing']:.1f}° | Time {data['time']}"
        )

    def update_data(self, payload: dict[str, Any]) -> None:
        try:
            freq_hz = float(payload[SCHEMA.FREQUENCY])
            bearing = float(payload[SCHEMA.BEARING])
        except (KeyError, TypeError, ValueError):
            return

        datetime_raw = payload.get(SCHEMA.DATETIME)
        if isinstance(datetime_raw, str):
            try:
                ts = datetime.fromisoformat(datetime_raw).timestamp()
            except ValueError:
                ts = datetime.now().timestamp()
        else:
            ts = datetime.now().timestamp()

        self._times_by_freq[freq_hz].append(ts)
        self._bearings_by_freq[freq_hz].append(bearing)
        self._meta_by_freq[freq_hz].append({
            'freq_label': self._format_freq_label(freq_hz),
            'bearing': bearing,
            'time': datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
        })

        series = self._series_by_freq.get(freq_hz)
        if series is None:
            series = self._create_series(freq_hz)

        times = self._times_by_freq[freq_hz]
        bearings = self._bearings_by_freq[freq_hz]
        metadata = self._meta_by_freq[freq_hz]

        series['line_item'].setData(times, bearings)
        series['scatter_item'].setData([
            {'pos': (t, b), 'data': m}
            for t, b, m in zip(times, bearings, metadata, strict=False)
        ])

        self._last_updated_label.setText(
            f"Last RX: {datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def clear(self) -> None:
        for series in self._series_by_freq.values():
            self._plot_widget.removeItem(series['line_item'])
            self._plot_widget.removeItem(series['scatter_item'])
        self._series_by_freq.clear()
        self._color_by_freq.clear()
        self._times_by_freq.clear()
        self._bearings_by_freq.clear()
        self._meta_by_freq.clear()
        self._last_updated_label.clear()

        was_legend_visible = self._legend.isVisible()
        legend_scene = self._legend.scene()
        if legend_scene is not None:
            legend_scene.removeItem(self._legend)
        self._legend = self._plot_widget.addLegend()
        self._configure_legend()
        self._legend.setVisible(was_legend_visible)
        self._legend_btn.setText('Hide Legend' if was_legend_visible else 'Show Legend')


class _PopupCloseFilter(QObject):
    """Event filter that intercepts close on popup window and calls pop_in instead."""

    def __init__(self, tab: _RdfStationTab) -> None:
        super().__init__(tab)
        self._tab = tab

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Close:
            self._tab._pop_in()
            return True
        return super().eventFilter(obj, event)


class _RdfStationTab(QWidget):
    def __init__(self, station_id: int) -> None:
        super().__init__()
        self._station_id = station_id
        self._popup: QWidget | None = None
        self._close_filter: _PopupCloseFilter | None = None

        self._plot = RDFBearingTimePlot(title=f'RDF Station {station_id}')
        self._plot._pop_btn.clicked.connect(self._toggle_pop)

        self._embed_container = QWidget()
        embed_layout = QVBoxLayout(self._embed_container)
        embed_layout.setContentsMargins(0, 0, 0, 0)
        embed_layout.addWidget(self._plot)

        self._placeholder = QLabel(f'Station {station_id} plot is shown in a separate window.')
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._embed_container)
        layout.addWidget(self._placeholder)

    def _toggle_pop(self) -> None:
        if self._popup is None:
            self._pop_out()
        else:
            self._pop_in()

    def _pop_out(self) -> None:
        popup = QWidget(None, Qt.WindowType.Window)
        popup.setWindowTitle(f'RDF Station {self._station_id} — Bearing vs Time')
        popup.resize(640, 480)

        popup_layout = QVBoxLayout(popup)
        popup_layout.setContentsMargins(4, 4, 4, 4)

        self._plot.setParent(popup)
        popup_layout.addWidget(self._plot)

        self._close_filter = _PopupCloseFilter(self)
        popup.installEventFilter(self._close_filter)

        self._popup = popup
        self._embed_container.hide()
        self._placeholder.show()
        self._plot.set_popped_out(True)
        popup.show()

    def _pop_in(self) -> None:
        if self._popup is None:
            return

        popup = self._popup
        if self._close_filter is not None:
            popup.removeEventFilter(self._close_filter)
            self._close_filter = None

        self._plot.setParent(self._embed_container)
        embed_layout = self._embed_container.layout()
        if embed_layout is not None:
            embed_layout.addWidget(self._plot)
        self._plot.show()

        self._popup = None
        popup.close()

        self._embed_container.show()
        self._placeholder.hide()
        self._plot.set_popped_out(False)

    def update_data(self, payload: dict[str, Any]) -> None:
        self._plot.update_data(payload)


class RdfView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle('RDF Bearing-Time')
        self.resize(640, 480)

        self._tabs = QTabWidget()
        self._tabs.setTabPosition(QTabWidget.TabPosition.West)

        self._station_tabs: dict[int, _RdfStationTab] = {}
        for station_id in (1, 2):
            tab = _RdfStationTab(station_id=station_id)
            self._station_tabs[station_id] = tab
            self._tabs.addTab(tab, f'Station {station_id}')

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._tabs)

    def update_rdf_data(self, payload: dict[str, Any]) -> None:
        try:
            station_id = int(payload[SCHEMA.STATION_ID])
        except (KeyError, TypeError, ValueError):
            return
        tab = self._station_tabs.get(station_id)
        if tab is not None:
            tab.update_data(payload)

    def closeEvent(self, event: QCloseEvent) -> None:
        for tab in self._station_tabs.values():
            tab._pop_in()
        event.ignore()
        self.hide()
