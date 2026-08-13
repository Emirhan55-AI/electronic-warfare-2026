"""Pyqtgraph spectrum and bounded waterfall view."""

from __future__ import annotations

from collections import deque

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QRectF, Qt
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
        pg.setConfigOption("background", "#0B0F14")
        pg.setConfigOption("foreground", "#98A7B7")
        pg.setConfigOption("antialias", False)
        pg.setConfigOption("useOpenGL", False)
        pg.setConfigOption("imageAxisOrder", "row-major")

        self._axis_mode = "offset"
        self._metric = "bin"
        self._waterfall_rows: deque[np.ndarray] = deque(maxlen=self.MAX_WATERFALL_ROWS)
        self.last_x_mhz = np.array([], dtype=np.float64)
        self.last_line_values = np.array([], dtype=np.float64)
        self.last_waterfall_values = np.empty((0, 0), dtype=np.float32)

        self.spectrum_plot = pg.PlotWidget()
        self.spectrum_plot.setObjectName("spectrumPlot")
        self.spectrum_plot.setTitle(TEXT["spectrum"], color="#E8EEF5", size="11pt")
        self.spectrum_plot.showGrid(x=True, y=True, alpha=0.16)
        self.spectrum_plot.setMenuEnabled(False)
        self.spectrum_plot.setMouseEnabled(x=True, y=True)
        self.spectrum_curve = self.spectrum_plot.plot(pen=pg.mkPen("#3A9DFF", width=1.5))
        self.noise_curve = self.spectrum_plot.plot(
            pen=pg.mkPen("#7F8D9C", width=1.0, style=Qt.PenStyle.DashLine)
        )
        self.threshold_curve = self.spectrum_plot.plot(
            pen=pg.mkPen("#F2C46D", width=1.2)
        )
        self.peak_markers = pg.ScatterPlotItem(
            size=7,
            pen=pg.mkPen("#FFB454", width=1.0),
            brush=pg.mkBrush(255, 180, 84, 130),
        )
        self.spectrum_plot.addItem(self.peak_markers)
        self.region_overlays: list[pg.LinearRegionItem] = []
        for _ in range(self.MAX_REGION_OVERLAYS):
            overlay = pg.LinearRegionItem(
                values=(0.0, 0.0),
                movable=False,
                pen=pg.mkPen("#FFB454", width=0.8),
                brush=pg.mkBrush(255, 180, 84, 28),
            )
            overlay.setZValue(-5)
            overlay.hide()
            self.spectrum_plot.addItem(overlay)
            self.region_overlays.append(overlay)
        self.parameter_overlay = pg.LinearRegionItem(
            values=(0.0, 0.0),
            movable=False,
            pen=pg.mkPen("#4DB6AC", width=1.2),
            brush=pg.mkBrush(77, 182, 172, 24),
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
        self.waterfall_plot.setTitle(TEXT["waterfall"], color="#E8EEF5", size="11pt")
        self.waterfall_plot.showGrid(x=True, y=False, alpha=0.12)
        self.waterfall_plot.setMenuEnabled(False)
        self.waterfall_plot.setMouseEnabled(x=True, y=False)
        self.waterfall_plot.setLabel("left", TEXT["history_frame"])
        self.waterfall_image = pg.ImageItem(axisOrder="row-major")
        self.waterfall_plot.addItem(self.waterfall_image)
        self.waterfall_empty_label = self._empty_label(
            self.waterfall_plot,
            TEXT["empty_history"],
        )
        color_map = pg.ColorMap(
            np.array([0.0, 0.55, 1.0]),
            np.array(
                [
                    [11, 15, 20, 255],
                    [20, 63, 94, 255],
                    [58, 157, 255, 255],
                ],
                dtype=np.ubyte,
            ),
        )
        self.waterfall_image.setLookupTable(color_map.getLookupTable(0.0, 1.0, 256))

        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Vertical)
        splitter.addWidget(self.spectrum_plot)
        splitter.addWidget(self.waterfall_plot)
        splitter.setSizes([430, 230])
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
        return len(self._waterfall_rows)

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
            self._waterfall_rows.append(np.asarray(waterfall, dtype=np.float32).copy())
        if self._waterfall_rows:
            self._set_history_available(True)
            image = np.stack(tuple(self._waterfall_rows), axis=0)
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
        self._waterfall_rows.clear()
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
