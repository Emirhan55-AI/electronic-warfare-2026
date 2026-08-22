"""Pyqtgraph spectrum and bounded waterfall view."""

from __future__ import annotations


import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtWidgets import QLabel, QSplitter, QVBoxLayout, QWidget

from reference.detection import DetectionFrameResult
from reference.parameters import ParameterFrameResult
from reference.spectrum import SpectrumDisplay
from reference.spectrum import SpectrumResult

from .ui_text import TEXT


class SpectrumView(QWidget):
    """Display one spectrum line and at most 128 real history rows."""

    MAX_WATERFALL_ROWS = 128
    MAX_REGION_OVERLAYS = 64

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        pg.setConfigOption("background", "#060A0F")
        pg.setConfigOption("foreground", "#8BA2B8")
        pg.setConfigOption("antialias", True)
        pg.setConfigOption("useOpenGL", False)
        pg.setConfigOption("imageAxisOrder", "row-major")

        self._axis_mode = "offset"
        self._metric = "bin"
        # Ring buffer: pre-allocated (MAX_ROWS, N_bins) — avoids np.stack each frame.
        # _ring_head counts total appended rows; _ring_fill tracks rows filled so far.
        self._ring_buf: np.ndarray = np.full(
            (self.MAX_WATERFALL_ROWS, 1), -140.0, dtype=np.float32
        )  # resized on first real row
        self._ring_head: int = 0
        self._ring_fill: int = 0
        self.last_x_mhz = np.array([], dtype=np.float64)
        self.last_line_values = np.array([], dtype=np.float64)
        self.last_waterfall_values = np.empty((0, 0), dtype=np.float32)

        self.spectrum_plot = pg.PlotWidget()
        self.spectrum_plot.setObjectName("spectrumPlot")
        self.spectrum_plot.setTitle(TEXT["spectrum"], color="#E2EEF8", size="10.5pt")
        self.spectrum_plot.showGrid(x=True, y=True, alpha=0.08)
        self.spectrum_plot.setMenuEnabled(False)
        self.spectrum_plot.setMouseEnabled(x=True, y=True)
        self.spectrum_curve = self.spectrum_plot.plot(pen=pg.mkPen("#38BDF8", width=1.2))
        self.noise_curve = self.spectrum_plot.plot(
            pen=pg.mkPen("#64748B", width=1.0, style=Qt.PenStyle.DashLine)
        )
        self.threshold_curve = self.spectrum_plot.plot(
            pen=pg.mkPen("#F59E0B", width=1.3)
        )
        self.peak_markers = pg.ScatterPlotItem(
            size=7,
            pen=pg.mkPen("#F59E0B", width=1.0),
            brush=pg.mkBrush(245, 158, 11, 140),
        )
        self.spectrum_plot.addItem(self.peak_markers)
        self.region_overlays: list[pg.LinearRegionItem] = []
        for _ in range(self.MAX_REGION_OVERLAYS):
            overlay = pg.LinearRegionItem(
                values=(0.0, 0.0),
                movable=False,
                pen=pg.mkPen("#F59E0B", width=0.8),
                brush=pg.mkBrush(245, 158, 11, 25),
            )
            overlay.setZValue(-5)
            overlay.hide()
            self.spectrum_plot.addItem(overlay)
            self.region_overlays.append(overlay)
        self.parameter_overlay = pg.LinearRegionItem(
            values=(0.0, 0.0),
            movable=False,
            pen=pg.mkPen("#10B981", width=1.2),
            brush=pg.mkBrush(16, 185, 129, 25),
        )
        self.parameter_overlay.hide()
        self.spectrum_plot.addItem(self.parameter_overlay)
        self._detection_visible = True
        self.spectrum_empty_label = self._empty_label(
            self.spectrum_plot,
            TEXT["empty_spectrum"],
        )

        self.waterfall_plot = pg.PlotWidget()
        self.waterfall_plot.setObjectName("waterfallPlot")
        self.waterfall_plot.setTitle(TEXT["waterfall"], color="#E2EEF8", size="10.5pt")
        self.waterfall_plot.showGrid(x=True, y=False, alpha=0.06)
        self.waterfall_plot.setMenuEnabled(False)
        self.waterfall_plot.setMouseEnabled(x=True, y=False)
        self.waterfall_plot.setLabel("left", TEXT["history_frame"])
        self.waterfall_image = pg.ImageItem(axisOrder="row-major")
        self.waterfall_plot.addItem(self.waterfall_image)
        self.waterfall_empty_label = self._empty_label(
            self.waterfall_plot,
            TEXT["empty_history"],
        )
        # Perceptually uniform viridis-based colormap; levels are driven by real
        # backend intensity values (bin_power_dbfs -140..0 dBFS).
        color_map = pg.ColorMap(
            np.linspace(0.0, 1.0, 5),
            np.array(
                [
                    [ 68,   1,  84, 255],  # derin mor  — düşük güç
                    [ 59,  82, 139, 255],  # koyu mavi
                    [ 33, 145, 140, 255],  # teal
                    [ 94, 201,  98, 255],  # yeşil
                    [253, 231,  37, 255],  # sarı       — tepe güç
                ],
                dtype=np.ubyte,
            ),
        )
        self.waterfall_image.setLookupTable(color_map.getLookupTable(0.0, 1.0, 256))

        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Vertical)
        splitter.addWidget(self.spectrum_plot)
        splitter.addWidget(self.waterfall_plot)
        splitter.setSizes([560, 240])
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        splitter.setChildrenCollapsible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)
        self.set_axis_mode("offset")
        self.set_metric("bin")
        self.clear_all()

    @staticmethod
    def _empty_label(parent: pg.PlotWidget, text: str) -> QLabel:
        label = QLabel(text, parent)
        label.setObjectName("emptyPlotHint")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        return label

    def _position_empty_labels(self) -> None:
        for plot, label in (
            (self.spectrum_plot, self.spectrum_empty_label),
            (self.waterfall_plot, self.waterfall_empty_label),
        ):
            label.setGeometry(plot.rect())

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)  # type: ignore[arg-type]
        self._position_empty_labels()
    def _set_spectrum_available(self, available: bool) -> None:
        self.spectrum_plot.getPlotItem().showAxis("left", available)
        self.spectrum_plot.getPlotItem().showAxis("bottom", available)
        self.spectrum_empty_label.setVisible(not available)

    def _set_history_available(self, available: bool) -> None:
        self.waterfall_plot.getPlotItem().showAxis("left", available)
        self.waterfall_plot.getPlotItem().showAxis("bottom", available)
        self.waterfall_empty_label.setVisible(not available)

    @property
    def waterfall_count(self) -> int:
        return self._ring_fill

    def set_axis_mode(self, mode: str) -> None:
        if mode not in {"offset", "absolute"}:
            raise ValueError("axis mode must be offset or absolute")
        self._axis_mode = mode
        label = TEXT["center_offset"] if mode == "offset" else TEXT["frequency"]
        self.spectrum_plot.setLabel("bottom", label, units="MHz")
        self.waterfall_plot.setLabel("bottom", label, units="MHz")

    def set_metric(self, metric: str) -> None:
        if metric not in {"bin", "psd"}:
            raise ValueError("metric must be bin or psd")
        self._metric = metric
        if metric == "bin":
            self.spectrum_plot.setLabel("left", "Bin/ton gücü", units="dBFS/bin")
            self.spectrum_plot.setYRange(-140.0, 0.0, padding=0.0)
        else:
            self.spectrum_plot.setLabel("left", "Güç spektral yoğunluğu", units="dBFS/Hz")
            self.spectrum_plot.setYRange(-180.0, 0.0, padding=0.0)

    def update_spectrum(
        self,
        line_display: SpectrumDisplay,
        waterfall_display: SpectrumDisplay,
        *,
        append_waterfall: bool = True,
        detection_result: DetectionFrameResult | None = None,
        spectrum_result: SpectrumResult | None = None,
        parameter_result: ParameterFrameResult | None = None,
    ) -> None:
        x_hz = (
            line_display.frequency_offset_hz
            if self._axis_mode == "offset"
            else line_display.frequency_absolute_hz
        )
        line = line_display.bin_power_dbfs if self._metric == "bin" else line_display.psd_dbfs_per_hz
        waterfall = (
            waterfall_display.bin_power_dbfs
            if self._metric == "bin"
            else waterfall_display.psd_dbfs_per_hz
        )
        self.last_x_mhz = np.asarray(x_hz / 1_000_000.0, dtype=np.float64)
        self.last_line_values = np.asarray(line, dtype=np.float64)
        self._set_spectrum_available(True)
        self.spectrum_curve.setData(self.last_x_mhz, self.last_line_values)
        self.spectrum_plot.setXRange(
            float(self.last_x_mhz[0]),
            float(self.last_x_mhz[-1]),
            padding=0.0,
        )
        self._update_detection_overlay(detection_result, spectrum_result)
        self._update_parameter_overlay(parameter_result)

        if append_waterfall:
            new_row = np.asarray(waterfall, dtype=np.float32)
            n_cols = new_row.shape[0]
            # Resize ring buffer lazily when first real data arrives or bin count changes.
            if self._ring_buf.shape[1] != n_cols:
                self._ring_buf = np.full(
                    (self.MAX_WATERFALL_ROWS, n_cols), -140.0, dtype=np.float32
                )
                self._ring_head = 0
                self._ring_fill = 0
            slot = self._ring_head % self.MAX_WATERFALL_ROWS
            self._ring_buf[slot] = new_row
            self._ring_head += 1
            self._ring_fill = min(self._ring_fill + 1, self.MAX_WATERFALL_ROWS)
        if self._ring_fill > 0:
            self._set_history_available(True)
            # Build ordered view: newest row at bottom (highest index).
            n = self._ring_fill
            rows = self.MAX_WATERFALL_ROWS
            if n == rows:
                # Full buffer: oldest row is one past current head.
                start = self._ring_head % rows
                image = np.concatenate(
                    [self._ring_buf[start:], self._ring_buf[:start]], axis=0
                )
            else:
                image = self._ring_buf[:n].copy()
            self.last_waterfall_values = image
            levels = (-140.0, 0.0) if self._metric == "bin" else (-180.0, 0.0)
            self.waterfall_image.setImage(image, autoLevels=False, levels=levels)
            width = float(self.last_x_mhz[-1] - self.last_x_mhz[0])
            self.waterfall_image.setRect(
                QRectF(float(self.last_x_mhz[0]), 0.0, width, float(image.shape[0]))
            )
            self.waterfall_plot.setXRange(
                float(self.last_x_mhz[0]),
                float(self.last_x_mhz[-1]),
                padding=0.0,
            )
            self.waterfall_plot.setYRange(0.0, float(max(image.shape[0], 2)), padding=0.0)

    def set_detection_visible(self, visible: bool) -> None:
        self._detection_visible = bool(visible)
        if not self._detection_visible:
            self.clear_detection_overlay()

    def _update_detection_overlay(
        self,
        detection: DetectionFrameResult | None,
        spectrum: SpectrumResult | None,
    ) -> None:
        self.clear_detection_overlay()
        if not self._detection_visible or detection is None or spectrum is None:
            return
        evaluated = detection.cells.evaluated_mask
        noise = detection.cells.noise_power
        threshold = detection.cells.threshold_power
        floor = 10.0 ** (-200.0 / 10.0)
        if self._metric == "bin":
            noise_values = 10.0 * np.log10(np.maximum(noise, floor))
            threshold_values = 10.0 * np.log10(np.maximum(threshold, floor))
        else:
            factor = (
                (spectrum.frame_length * spectrum.window_coherent_gain) ** 2
                / (spectrum.sample_rate_hz * spectrum.window_power_sum)
            )
            noise_values = 10.0 * np.log10(np.maximum(noise * factor, floor))
            threshold_values = 10.0 * np.log10(np.maximum(threshold * factor, floor))
        noise_values = np.where(evaluated, noise_values, np.nan)
        threshold_values = np.where(evaluated, threshold_values, np.nan)
        self.noise_curve.setData(self.last_x_mhz, noise_values)
        self.threshold_curve.setData(self.last_x_mhz, threshold_values)

        strongest = sorted(
            detection.regions,
            key=lambda region: (-region.peak_power, region.start_bin, region.end_bin),
        )[: self.MAX_REGION_OVERLAYS]
        peaks_x: list[float] = []
        peaks_y: list[float] = []
        for overlay, region in zip(self.region_overlays, strongest, strict=False):
            start = float(self.last_x_mhz[region.start_bin])
            end = float(self.last_x_mhz[region.end_bin])
            if end <= start:
                end = start + spectrum.bin_spacing_hz / 1_000_000.0
            overlay.setRegion((start, end))
            overlay.show()
            peaks_x.append(float(self.last_x_mhz[region.peak_bin]))
            peaks_y.append(float(self.last_line_values[region.peak_bin]))
        self.peak_markers.setData(peaks_x, peaks_y)

    def clear_detection_overlay(self) -> None:
        self.noise_curve.clear()
        self.threshold_curve.clear()
        self.peak_markers.clear()
        for overlay in self.region_overlays:
            overlay.hide()
        self.parameter_overlay.hide()

    def _update_parameter_overlay(self, result: ParameterFrameResult | None) -> None:
        self.parameter_overlay.hide()
        if result is None or not result.events or self.last_x_mhz.size != 4096:
            return
        bandwidth = result.events[0].bandwidth
        if (
            bandwidth.lower_edge_state != "valid"
            or bandwidth.upper_edge_state != "valid"
            or bandwidth.bandwidth_state != "valid"
            or bandwidth.lower_shifted_bin is None
            or bandwidth.upper_shifted_bin is None
        ):
            return
        start = float(self.last_x_mhz[bandwidth.lower_shifted_bin])
        end = float(self.last_x_mhz[bandwidth.upper_shifted_bin])
        if end <= start:
            return
        self.parameter_overlay.setRegion((start, end))
        self.parameter_overlay.show()

    def clear_history(self) -> None:
        self._ring_head = 0
        self._ring_fill = 0
        # Zero the ring buffer in-place so stale data cannot leak across sessions.
        self._ring_buf[:] = -140.0
        self.last_waterfall_values = np.empty((0, 0), dtype=np.float32)
        self.waterfall_image.clear()
        self._set_history_available(False)

    def clear_all(self) -> None:
        self.clear_history()
        self.last_x_mhz = np.array([], dtype=np.float64)
        self.last_line_values = np.array([], dtype=np.float64)
        self.spectrum_curve.clear()
        self.clear_detection_overlay()
        self._set_spectrum_available(False)
        self._position_empty_labels()


class AnalysisSpectrumView(QWidget):
    """Focused spectrum with a bounded, draggable operator span."""

    span_changed = Signal(int, int)
    carrier_selected = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.plot = pg.PlotWidget()
        self.plot.setObjectName("analysisSpectrumPlot")
        self.plot.setTitle(TEXT["analysis_spectrum"], color="#E8EEF5", size="11pt")
        self.plot.setLabel("bottom", TEXT["frequency"], units="MHz")
        self.plot.setLabel("left", "Bin/ton gücü", units="dBFS/bin")
        self.plot.showGrid(x=True, y=True, alpha=0.16)
        self.plot.setMenuEnabled(False)
        self.curve = self.plot.plot(pen=pg.mkPen("#3A9DFF", width=1.5))
        self.band_region = pg.LinearRegionItem(
            values=(0.0, 0.0), movable=False,
            pen=pg.mkPen("#35B8D1", width=0.8), brush=pg.mkBrush(53, 184, 209, 22),
        )
        self.plot.addItem(self.band_region)
        self.band_region.hide()
        self.lower_marker = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen("#35B8D1", width=1.0))
        self.carrier_marker = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen("#F2C46D", width=1.4))
        self.upper_marker = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen("#35B8D1", width=1.0))
        for marker in (self.lower_marker, self.carrier_marker, self.upper_marker):
            self.plot.addItem(marker)
            marker.hide()
        self.region = pg.LinearRegionItem(
            values=(0.0, 0.0), movable=True,
            pen=pg.mkPen("#4DB6AC", width=1.5), brush=pg.mkBrush(77, 182, 172, 40),
        )
        self.plot.addItem(self.region)
        self.region.hide()
        self.region.sigRegionChangeFinished.connect(self._region_finished)
        self._frequencies = np.array([], dtype=np.float64)
        self.last_x_data = np.array([], dtype=np.float64)
        self.last_y_data = np.array([], dtype=np.float64)
        self._bin_spacing_mhz = 0.0
        self._blocking = False
        self.plot.scene().sigMouseClicked.connect(self._carrier_clicked)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot)

    def set_spectrum(self, display: SpectrumDisplay) -> None:
        frequencies = np.asarray(display.frequency_absolute_hz / 1_000_000.0, dtype=np.float64)
        power = np.asarray(display.bin_power_dbfs, dtype=np.float64)
        valid = np.isfinite(frequencies) & np.isfinite(power)
        if frequencies.size != power.size or not np.any(valid):
            self.clear_span()
            return
        self._frequencies = frequencies
        self.last_x_data = frequencies[valid]
        self.last_y_data = power[valid]
        self._bin_spacing_mhz = float(self._frequencies[1] - self._frequencies[0])
        self.curve.setData(self.last_x_data, self.last_y_data)

    def set_event_markers(self, *, lower_hz: float, carrier_hz: float, upper_hz: float) -> None:
        """Render verified event bounds on the existing real spectrum curve."""
        lower, carrier, upper = (float(value) / 1_000_000.0 for value in (lower_hz, carrier_hz, upper_hz))
        if not lower < carrier < upper:
            return
        self.lower_marker.setValue(lower)
        self.carrier_marker.setValue(carrier)
        self.upper_marker.setValue(upper)
        self.band_region.setRegion((lower, upper))
        for item in (self.lower_marker, self.carrier_marker, self.upper_marker, self.band_region):
            item.show()

    def clear_event_markers(self) -> None:
        for item in (self.lower_marker, self.carrier_marker, self.upper_marker, self.band_region):
            item.hide()

    def set_span(self, lower_bin: int, upper_bin: int) -> None:
        if self._frequencies.size != 4096:
            return
        self._blocking = True
        self.region.setBounds((float(self._frequencies[20]), float(self._frequencies[4075])))
        self.region.setRegion((float(self._frequencies[lower_bin]), float(self._frequencies[upper_bin])))
        self.region.show()
        margin = max(16, upper_bin - lower_bin + 1)
        start = max(20, lower_bin - margin)
        end = min(4075, upper_bin + margin)
        self.plot.setXRange(float(self._frequencies[start]), float(self._frequencies[end]), padding=0.0)
        self._blocking = False

    def clear_span(self) -> None:
        self.region.hide()
        self.curve.clear()
        self._frequencies = np.array([], dtype=np.float64)
        self.last_x_data = np.array([], dtype=np.float64)
        self.last_y_data = np.array([], dtype=np.float64)
        self.clear_event_markers()

    def nudge(self, amount_bins: int) -> None:
        if not self.region.isVisible() or self._bin_spacing_mhz == 0.0:
            return
        lower, upper = self.region.getRegion()
        delta = amount_bins * self._bin_spacing_mhz
        self.region.setRegion((lower + delta, upper + delta))
        self._region_finished()

    def _region_finished(self) -> None:
        if self._blocking or self._frequencies.size != 4096:
            return
        lower_mhz, upper_mhz = self.region.getRegion()
        lower = int(np.searchsorted(self._frequencies, lower_mhz, side="right") - 1)
        upper = int(np.searchsorted(self._frequencies, upper_mhz, side="left"))
        lower = min(max(lower, 20), 4068)
        upper = min(max(upper, lower + 7), 4075)
        if upper - lower + 1 > 512:
            upper = lower + 511
        self.set_span(lower, upper)
        self.span_changed.emit(lower, upper)

    def _carrier_clicked(self, event: object) -> None:
        if self._frequencies.size == 0:
            return
        position = getattr(event, "scenePos", lambda: None)()
        if position is None:
            return
        point = self.plot.getPlotItem().vb.mapSceneToView(position)
        frequency_mhz = float(point.x())
        index = int(np.argmin(np.abs(self._frequencies - frequency_mhz)))
        selected = float(self._frequencies[index])
        self.carrier_marker.setValue(selected)
        self.carrier_marker.show()
        self.carrier_selected.emit(selected * 1_000_000.0)
